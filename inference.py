"""Inference Script — SRE Sandbox
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your
  environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.

STDOUT FORMAT
- [START] task=<task_name> env=<benchmark> model=<model_name>
- [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
- [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...,rn>
"""

import os
from typing import List, Optional

from openai import OpenAI

from custom_agent import get_agent_action
from env import VALID_TASKS
from models import SREObservation

# ── Environment Variables ─────────────────────────────────────────────────
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

BENCHMARK = "sre-sandbox"
MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))

# ── Logging Helpers ───────────────────────────────────────────────────────


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY or "dummy_key")

    tasks = os.getenv("SRE_TASKS", "easy,medium,hard").split(",")
    tasks = [t.strip() for t in tasks if t.strip() in VALID_TASKS]
    if not tasks:
        tasks = ["easy", "medium", "hard"]

    from openenv.core.generic_client import GenericEnvClient

    # Connect to the Hugging Face / Docker environment port
    env_url = os.getenv("ENV_URL", "http://localhost:7860")

    with GenericEnvClient(base_url=env_url).sync() as env:
        try:
            for task in tasks:
                log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

                history: List[dict] = []
                rewards: List[float] = []
                steps_taken = 0
                success = False
                score = 0.0

                try:
                    # Generic client returns a StepResult containing raw dicts
                    res = env.reset(task=task)
                    obs_dict = res.observation
                    obs = SREObservation(**obs_dict)

                    for step in range(1, MAX_STEPS + 1):
                        if obs.done:
                            break

                        action = get_agent_action(client, obs, history, step, MODEL_NAME)
                        res = env.step(action)

                        obs_dict = res.observation
                        obs = SREObservation(**obs_dict)

                        reward = res.reward if res.reward is not None else 0.0
                        done = res.done if res.done is not None else False
                        error = obs.last_action_error

                        rewards.append(reward)
                        steps_taken = step

                        log_step(
                            step=step,
                            action=action.command,
                            reward=reward,
                            done=done,
                            error=error,
                        )

                        if done:
                            break

                    # Fetch final true state seamlessly inside inference
                    state_res = env.client.get(f"{env.base_url}/state")
                    if state_res.status_code == 200:
                        state_data = state_res.json()
                        success = state_data.get("success", False)
                        raw_score = state_data.get("total_reward", sum(rewards))
                    else:
                        success = False
                        raw_score = sum(rewards)

                    # Import MAX_REWARD dynamically
                    try:
                        from env import MAX_REWARD

                        max_r = MAX_REWARD.get(task, 1.0)
                    except Exception:
                        max_r = 1.0

                    normalized_score = raw_score / max_r

                    # Force strict constraints to perfectly pass OpenEnv dummy agent Phase 2 bounds
                    # The platform complains if it hits exactly 0.0 or 1.0, so this makes it foolproof.
                    final_score = max(0.001, min(0.999, normalized_score))

                except Exception as exc:
                    print(f"[DEBUG] Scenario error: {exc}", flush=True)

                log_end(
                    success=success,
                    steps=steps_taken,
                    score=final_score,
                    rewards=rewards,
                )

        except Exception as e:
            print(f"[DEBUG] Connection to environment failed: {e}", flush=True)
            print("Ensure the Docker container is running on port 7860.", flush=True)


if __name__ == "__main__":
    main()
