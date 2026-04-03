"""
Example: HTTP API client for the SRE Sandbox.

This script demonstrates how to test your own agent against the
sandbox using the REST API. Works with any language that can make
HTTP requests — this Python version is just a reference.

Usage:
    1. Start the server:  python server/app.py
    2. Run this client:   python examples/client_http.py
"""

import requests

BASE_URL = "http://localhost:8000"


def main():
    # ── Check server health ───────────────────────────────────────────
    health = requests.get(f"{BASE_URL}/health").json()
    print(f"Server status: {health['status']}")
    print(f"Available scenarios: {health['available_scenarios']}\n")

    # ── Run the 'easy' scenario ───────────────────────────────────────
    task = "easy"
    print(f"{'━' * 50}")
    print(f"▶ Starting scenario: {task.upper()}")
    print(f"{'━' * 50}")

    # Reset — start the scenario
    obs = requests.post(f"{BASE_URL}/reset", json={"task": task}).json()
    print(f"Ticket: {obs['ticket_context']}")

    # ── Your agent logic goes here ────────────────────────────────────
    # Replace this with YOUR agent's decision-making!
    actions = [
        {
            "phase": "research",
            "command": "service nginx status",
            "rationale": "Check if nginx is running",
        },
        {
            "phase": "execute",
            "command": "service nginx restart",
            "rationale": "Restart nginx to restore service",
        },
    ]

    total_reward = 0.0
    for i, action in enumerate(actions, 1):
        print(f"\n[Step {i}] ({action['phase']}) {action['command']}")

        result = requests.post(f"{BASE_URL}/step", json=action).json()

        reward = result["reward"]
        done = result["done"]
        total_reward += reward

        print(f"  stdout: {result['observation']['stdout'][:100]}")
        print(f"  reward: {reward:.2f} (total: {total_reward:.2f})")
        print(f"  done: {done}")

        if done:
            success = result["info"].get("success", False)
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status} — Total reward: {total_reward:.2f}")
            break

    # ── Check historical metrics ──────────────────────────────────────
    print(f"\n{'━' * 50}")
    metrics = requests.get(f"{BASE_URL}/metrics").json()
    print(f"Historical runs: {metrics.get('total_runs', 0)}")


if __name__ == "__main__":
    main()
