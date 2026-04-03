"""
Example: Python direct-import client for the SRE Sandbox.

This script demonstrates how to test your own Python agent against
the sandbox by importing the DevOpsEnv directly — no server needed.

Usage:
    python examples/client_python.py

Prerequisites:
    - Docker must be running
    - pip install -r requirements.txt
"""

from env import DevOpsEnv
from models import GSDAction, SREObservation


class MyCustomAgent:
    """
    Example agent — replace this with your own logic!

    Your agent must implement:
        reset()                              → called at scenario start
        get_action(task, obs) → GSDAction    → return the next action
    """

    def __init__(self):
        self.history: list[str] = []

    def reset(self):
        self.history = []

    def get_action(self, task: str, obs: SREObservation) -> GSDAction:
        """
        Your agent logic goes here.

        Use obs.ticket_context, obs.stdout, obs.stderr, obs.exit_code
        to decide what to do next.
        """
        step = len(self.history) + 1

        # ── Simple rule-based example ─────────────────────────────────
        # Replace this with your LLM call, RL policy, or any logic!

        if step == 1:
            # Always start by investigating
            action = GSDAction(
                phase="research",
                command="cat /var/log/nginx/error.log 2>/dev/null; service nginx status 2>&1; df -h",
                rationale="Gathering initial diagnostics: logs, service status, disk usage",
            )
        elif "nginx" in obs.stderr.lower() or "nginx" in obs.stdout.lower():
            action = GSDAction(
                phase="execute",
                command="service nginx restart",
                rationale="Nginx issue detected, attempting restart",
            )
        else:
            action = GSDAction(
                phase="research",
                command="echo 'Need more investigation'",
                rationale="Not sure what to do next",
            )

        self.history.append(action.command)
        return action


def main():
    agent = MyCustomAgent()
    tasks = ["easy", "medium"]  # Start with easier ones
    max_steps = 10

    with DevOpsEnv() as env:
        for task in tasks:
            print(f"\n{'━' * 50}")
            print(f"▶ Scenario: {task.upper()}")
            print(f"{'━' * 50}")

            obs = env.reset(task)
            agent.reset()
            print(f"Ticket: {obs.ticket_context}\n")

            done = False
            step = 0
            total_reward = 0.0

            while not done and step < max_steps:
                step += 1
                action = agent.get_action(task, obs)
                print(f"[Step {step}] ({action.phase}) {action.command}")

                obs, reward, done, info = env.step(action)
                total_reward += reward
                print(f"  reward={reward:.2f}  total={total_reward:.2f}  done={done}")

            success = info.get("success", False)
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status} — {task} — reward={total_reward:.2f}, steps={step}")


if __name__ == "__main__":
    main()
