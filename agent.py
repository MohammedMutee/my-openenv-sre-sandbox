"""
AI Agents for the SRE Sandbox.

Provides both a deterministic ``MockAgent`` (for baseline testing) and
a ``GeminiAgent`` that uses Google's Gemini API for real LLM-powered
SRE troubleshooting.
"""

import json
import logging
import re

import google.generativeai as genai

from config import settings
from models import GSDAction, SREObservation

logger = logging.getLogger(__name__)

# ── System Prompt ─────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) AI agent operating inside \
a Linux Docker container. Your job is to diagnose and fix broken infrastructure.

## GSD Workflow
You MUST follow the GSD (Get Shit Done) phases in order:
1. **research** — Gather information (read logs, check service status, inspect configs)
2. **plan** — Reason about root cause (you may skip this if obvious)
3. **execute** — Apply fixes (edit configs, restart services, clean resources)
4. **verify** — Confirm the fix worked (check HTTP status, service status)

## Rules
- Run ONE command per step. Be precise.
- NEVER run destructive commands like `rm -rf /` or `mkfs`.
- Always explain your rationale.
- If you're stuck, investigate more before acting.

## Response Format
Respond with ONLY a JSON object (no markdown, no backticks):
{"phase": "<research|plan|execute|verify>", "command": "<bash command>", "rationale": "<why>"}
"""


class MockAgent:
    """
    Deterministic mock agent with pre-scripted actions per scenario.
    Used for baseline testing of the evaluation loop.
    """

    def __init__(self) -> None:
        self.step_counter = 0

    def reset(self) -> None:
        self.step_counter = 0

    def get_action(self, task: str, obs: SREObservation) -> GSDAction:
        """Return the next pre-scripted action for the given scenario."""
        self.step_counter += 1

        if task == "easy":
            return GSDAction(
                phase="execute",
                command="service nginx restart",
                rationale="Nginx is down — restart it.",
            )

        elif task == "medium":
            actions = {
                1: GSDAction(
                    phase="research",
                    command="cat /var/log/nginx/error.log",
                    rationale="Checking error logs for config issues.",
                ),
                2: GSDAction(
                    phase="execute",
                    command=(
                        "echo 'server { listen 80; root /var/www/html; "
                        "index index.html; }' > /etc/nginx/sites-available/default"
                    ),
                    rationale="Overwriting broken config with a clean default.",
                ),
                3: GSDAction(
                    phase="verify",
                    command="service nginx restart",
                    rationale="Restarting to verify the fix.",
                ),
            }
            if self.step_counter in actions:
                return actions[self.step_counter]

        elif task == "hard":
            actions = {
                1: GSDAction(
                    phase="research",
                    command="df -h",
                    rationale="Checking disk usage to understand the situation.",
                ),
                2: GSDAction(
                    phase="execute",
                    command="rm -f /var/log/nginx/access.log",
                    rationale="Removing bloated access log to recover disk space.",
                ),
                3: GSDAction(
                    phase="execute",
                    command="sed -i 's/port = 0000/port = 5432/g' /etc/postgresql/14/main/postgresql.conf",
                    rationale="Fixing Postgres port in config.",
                ),
                4: GSDAction(
                    phase="execute",
                    command="service postgresql restart",
                    rationale="Restarting database after config fix.",
                ),
                5: GSDAction(
                    phase="verify",
                    command="service nginx restart",
                    rationale="Restarting webserver to verify full recovery.",
                ),
            }
            if self.step_counter in actions:
                return actions[self.step_counter]

        return GSDAction(
            phase="research",
            command="echo 'No further actions'",
            rationale="No more pre-scripted actions.",
        )


class GeminiAgent:
    """
    LLM-powered SRE agent using Google's Gemini API.

    Maintains conversation history for multi-step reasoning.
    Falls back to safe no-op if the API fails.
    """

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set. Add it to your .env file.")

        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=_SYSTEM_PROMPT,
        )
        self.chat = None
        logger.info("GeminiAgent initialised with model: %s", settings.gemini_model)

    def reset(self) -> None:
        """Start a fresh conversation for a new scenario."""
        self.chat = self.model.start_chat(history=[])

    def get_action(self, task: str, obs: SREObservation) -> GSDAction:
        """
        Send the current observation to Gemini and parse its response
        into a structured GSDAction.
        """
        if self.chat is None:
            self.reset()

        # Build the prompt from the observation
        prompt_parts = []
        if obs.ticket_context:
            prompt_parts.append(f"## Ticket\n{obs.ticket_context}")

        prompt_parts.append(f"## Current Directory\n{obs.current_directory}")

        if obs.stdout.strip():
            prompt_parts.append(f"## stdout\n```\n{obs.stdout.strip()}\n```")
        if obs.stderr.strip():
            prompt_parts.append(f"## stderr\n```\n{obs.stderr.strip()}\n```")

        prompt_parts.append(f"## Exit Code\n{obs.exit_code}")
        prompt_parts.append("\nWhat is your next action? Respond with ONLY a JSON object.")

        prompt = "\n\n".join(prompt_parts)

        try:
            response = self.chat.send_message(prompt)
            raw_text = response.text.strip()
            logger.debug("Gemini raw response: %s", raw_text)

            action_data = self._parse_response(raw_text)
            return GSDAction(**action_data)

        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            return GSDAction(
                phase="research",
                command="echo 'LLM error — performing no-op'",
                rationale=f"Gemini API returned an error: {exc}",
            )

    @staticmethod
    def _parse_response(text: str) -> dict:
        """
        Extract JSON from the LLM response, handling markdown fences
        and other wrapping that models sometimes add.
        """
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = cleaned.strip().rstrip("`")

        # Try to find a JSON object in the text
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())

        # Last resort: try parsing the whole cleaned text
        return json.loads(cleaned)


def create_agent(agent_type: str | None = None):
    """
    Factory function for creating the appropriate agent.

    Args:
        agent_type: ``'mock'`` or ``'gemini'``. Defaults to config value.

    Returns:
        An agent instance with ``reset()`` and ``get_action()`` methods.
    """
    agent_type = agent_type or settings.agent_type

    if agent_type == "gemini":
        logger.info("Creating Gemini LLM agent …")
        return GeminiAgent()
    elif agent_type == "mock":
        logger.info("Creating Mock agent …")
        return MockAgent()
    else:
        raise ValueError(f"Unknown agent type: {agent_type}. Use 'mock' or 'gemini'.")
