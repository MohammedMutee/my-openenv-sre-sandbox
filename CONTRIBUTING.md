# Contributing — Bring Your Own Agent (BYOA)

This comprehensive guide explains how to test **your own AI agent** against the SRE Sandbox scenarios.

## 🧠 Option 1: The `custom_agent.py` Interface (Recommended)
This environment is thoroughly decoupled from its evaluation runner (`inference.py`). 

To bring your own agent without worrying about docker connection formatting, state loops, or log aggregation:
1. Open [`custom_agent.py`](custom_agent.py).
2. Override the `SYSTEM_PROMPT` with your own system instructions.
3. Modify the `get_agent_action` function to ping **LangChain**, **CrewAI**, **vLLM**, or any other framework you desire. 
4. Just ensure the function returns an `SREAction` object.
5. Run the standard loop natively: `python3 inference.py`.

---

## 🌐 Option 2: OpenEnv HTTP Server (Any Language)
Because this environment conforms to the OpenEnv specification, it natively bundles a generic HTTP wrapper running on port **7860**. You can connect agents built in **Go, Rust, or JavaScript** to it!

### 1. Start the Container
```bash
docker build -t sre-sandbox .
docker run -p 7860:7860 sre-sandbox
```

### 2. Check Available Scenarios
```bash
curl http://localhost:7860/health
```

### 3. Reset — Initialize Scenario
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "easy"}'
```

---

## 🐍 Option 3: Python Generic Client
If you're writing python but want to avoid the `inference.py` script entirely, you can securely connect to the container API using the OpenEnv Client:

```python
from openenv.core.generic_client import GenericEnvClient

with GenericEnvClient(base_url="http://localhost:7860").sync() as env:
    # 1. Reset
    res = env.reset(task="easy")
    print(res.observation)
    
    # 2. Step
    action = {"phase": "research", "command": "cat /var/log/nginx/error.log", "rationale": "debug"}
    res = env.step(action)
    print(f"Reward: {res.reward}")
```

---

## 🏗️ Action Schema — `SREAction`

| Field | Type | Required | Description |
|---|---|---|---|
| `phase` | `"research"`, `"plan"`, `"execute"`, `"verify"` | ✅ | GSD workflow phase |
| `command` | `string` | ✅ | Bash command to run in the container |
| `rationale` | `string` | ✅ | Why you're running this command |

---

## 🔍 Observation Schema — `SREObservation`

| Field | Type | Description |
|---|---|---|
| `stdout` | `string` | Command output |
| `stderr` | `string` | Error output |
| `exit_code` | `int` | 0 = success |
| `current_directory` | `string` | Working directory after command |
| `ticket_context` | `string?` | The SRE ticket (only on reset) |

---

## ⚖️ Scoring and Blocking
The `CommandSanitizer` operates seamlessly to protect the Hugging Face space. Let your agent roam free—any overly dangerous commands (`rm -rf /`, `shutdown`, fork bombs) will be internally trapped, skipping execution and automatically penalizing the agent natively by `-0.5`. 

*(Standard rewards scale out between 0.0 — 1.0 gracefully.)*
