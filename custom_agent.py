import json
import re
import textwrap
from typing import List

from openai import OpenAI
from models import SREAction, SREObservation

# ── Custom Prompt ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert Site Reliability Engineer (SRE) AI agent.
    You are given a broken Linux server and a support ticket describing the problem.
    Your goal is to diagnose and fix the issue using the GSD (Get Shit Done) workflow:

    Phases:
    - research: Gather information (read logs, check status, inspect configs)
    - plan: Reason about root cause (optional, can echo your plan)
    - execute: Apply fixes (restart services, edit configs, clean up)
    - verify: Confirm the fix worked (curl, systemctl status, etc.)

    IMPORTANT RULES:
    - Always start with "research" to understand the problem
    - Move to "execute" once you know the fix
    - Each response must be a valid JSON object with these fields:
      {"phase": "...", "command": "...", "rationale": "..."}
    - command must be a single bash command
    - Do NOT use destructive commands like rm -rf /
    - Be concise and efficient
""").strip()

# ── Custom Agent Logic ────────────────────────────────────────────────────


def get_agent_action(
    client: OpenAI,
    obs: SREObservation,
    history: List[dict],
    step: int,
    model_name: str,
) -> SREAction:
    """
    Call your LLM to get the next SRE action.
    This function is dynamically executed per-step by inference.py.
    """
    # 1. Build context
    user_content = f"""Step {step}
Ticket: {obs.ticket_context or "N/A"}
Last command output (stdout): {obs.stdout[:500] if obs.stdout else "N/A"}
Last command stderr: {obs.stderr[:300] if obs.stderr else "N/A"}
Exit code: {obs.exit_code}
Working directory: {obs.current_directory}

Respond with a JSON object: {{"phase": "...", "command": "...", "rationale": "..."}}"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-6:])  # Remember last 3 exchanges to save tokens
    messages.append({"role": "user", "content": user_content})

    try:
        # 2. Call OpenAI / vLLM / Hugging Face Router
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        # 3. Parse JSON from reasoning payload
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        data = json.loads(text)

        action = SREAction(
            phase=data.get("phase", "execute"),
            command=data.get("command", "echo 'no command'"),
            rationale=data.get("rationale", "LLM response"),
        )

        # Record LLM interaction back into conversation history
        history.append({"role": "user", "content": user_content})
        history.append({"role": "assistant", "content": text})

        return action

    except Exception as exc:
        print(f"[DEBUG] LLM parse error: {exc}", flush=True)
        # 4. Fallback execution if the model refuses JSON formatting or encounters 401 error
        return SREAction(
            phase="research",
            command="cat /var/log/nginx/error.log 2>/dev/null; service nginx status 2>&1",
            rationale=f"Fallback after LLM error: {exc}",
        )
