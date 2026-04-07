---
title: SRE Sandbox
emoji: 🐳
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# SRE Sandbox — OpenEnv Competition Track

An **OpenEnv-compliant** sandbox that evaluates AI SRE agents by deliberately breaking Linux infrastructure and measuring how effectively they diagnose and fix the issues via native bash commands.

This environment perfectly follows the **OpenEnv** specifications, running directly on Hugging Face Spaces and testing large language models realistically.

## 🚀 Hugging Face Space & OpenEnv Spec
- **Subprocess native**: The environment breaks its *own* container natively via `subprocess`. No nested Docker API requirements, making it 100% compliant with standard HF Spaces.
- **Strict Spec Definitions**: Employs `openenv.core.env_server.interfaces.Environment`. Uses `SREAction`, `SREObservation`, and `SREState` derived cleanly from standard `openenv` types.
- **Automatic Server**: Uses `HTTPEnvServer` wrapper running on port `7860` natively, ensuring `/reset`, `/state`, `/step`, `/metadata`, and `/schema` work perfectly for external REST access.
- **Inference Ready**: Implements all strict competition standard logs: `[START]`, `[STEP]`, `[END]`.

## 🛠️ Quick Start (Clone & Test)

**1. Clone the environment and configure Python**
```bash
git clone https://github.com/MohammedMutee/my-openenv-sre-sandbox.git
cd my-openenv-sre-sandbox
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

**2. Verify compliance using OpenEnv tool**
```bash
openenv validate
```

**3. Test the baseline inference**
```bash
# Will use API_BASE_URL, MODEL_NAME, and HF_TOKEN. 
# Safe mock defaults kick in if keys are missing to guarantee format tests pass.
python inference.py
```

**4. 🧠 Bring Your Own Agent (BYOA)**
The environment is decoupled entirely from prompt engineering. To test your own AI agent:
1. Open [`custom_agent.py`](custom_agent.py)
2. Modify `SYSTEM_PROMPT` or the `get_agent_action` logic to connect your own framework (LangChain, AutoGen, pure OpenAI, etc.)
3. Run `python inference.py` to evaluate your agent's performance against the leaderboard!

**5. Test Hugging Face deployment locally (Docker)**
```bash
docker build -t sre-sandbox .
docker run -p 7860:7860 sre-sandbox
```
*(You can now send POST requests to `http://localhost:7860/reset`)*

## 🧱 Scenarios (8 Total)

| Scenario | Sabotage | Difficulty |
|---|---|---|
| **easy** | Nginx process killed | ⭐ |
| **medium** | Nginx config syntax error | ⭐⭐ |
| **hard** | 500MB disk fill + Postgres port corrupted | ⭐⭐⭐ |
| **dns** | resolv.conf wiped | ⭐⭐ |
| **firewall** | iptables blocking ports 80/443 | ⭐⭐ |
| **permissions** | Web root + config chmod 000 | ⭐⭐ |
| **resource** | /tmp filled + CPU consumers spawned | ⭐⭐⭐ |
| **cascade** | Nginx upstream broken + Postgres auth reject + log flood | ⭐⭐⭐⭐ |

## 📈 Dense Reward System
Instead of simple binary grades, this custom environment parses agent bash execution with regex to reward strong methodologies. 

| Signal | Reward | Examples |
|---|---|---|
| Diagnostic | +0.2 | `cat`, `tail`, `grep` on logs; `df`, `ss`, `systemctl status` |
| Phase bonus | +0.1 | Research phase + diagnostic, or Execute phase + remediation |
| Remediation | +0.3 | `service restart`, `sed -i`, `chmod`, `iptables -F` |
| Environment fixed | +0.5 | HTTP 200 + DB OK |
| Blocked command | −0.5 | `rm -rf /`, `mkfs`, `shutdown` (Blocked securely without execution) |

*(Normalised gracefully between 0.0 - 1.0 per task constraint via `get_normalized_score()`)*

## 🔒 Security Gate
`CommandSanitizer` stops the LLM from destroying the hugging face space securely.
- **17 blocked patterns**: `rm -rf /`, `mkfs`, `dd /dev/`, fork bombs.
- Safe overrides: Log file removal `/var/log/*` allowed. 

## 🧪 Tests
Over 90+ tests guarantee scenario loading and rewards functionality perfectly.

```bash
pytest tests/ -v
```

## 🗂️ Project Structure

```
my-openenv/
├── custom_agent.py        # Pluggable BYOA (Bring Your Own Agent) architecture
├── env.py                 # Core SREEnvironment engine + grader (Subprocess Native)
├── inference.py           # CLI evaluation runner + OpenEnv client 
├── models.py              # Pydantic Action + Observation schemas based on openenv objects
├── security.py            # Command sanitizer (blocklist + overrides) protects HF Space
├── rewards.py             # Regex-based reward calculator
├── openenv.yaml           # Spec configurations and model metadata
├── server/
│   └── app.py             # FastAPI OpenEnv wrapper bound to port 7860
├── examples/
│   ├── client_http.py     # HTTP API client example
│   └── client_python.py   # Python Generic Client directly
├── scripts/
│   ├── scenario_easy.sh   ... scenario_cascade.sh (8 scripts defining SABOTAGE)
├── tests/
│   ├── test_models.py     ... test_env.py (94 rigorous tests)
├── .github/workflows/
│   └── ci.yml             # Lint → Test → Docker validation
├── Dockerfile             # Ubuntu 22.04 unified container natively hosting APIs + Bash
├── CONTRIBUTING.md        # Guide: pinging the environment via OpenEnv clients
├── LICENSE                # MIT License
├── pyproject.toml         # v2.0.0 with openenv-core
└── REPORT.md              # Detailed final deliverables report
```

## License
MIT
