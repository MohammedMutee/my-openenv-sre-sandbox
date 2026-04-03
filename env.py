"""
SRE Sandbox — OpenEnv-compliant Environment (Local Subprocess Mode).

Implements the ``openenv.Environment`` interface using local system
commands (subprocess) instead of Docker-in-Docker, ensuring full
compatibility with Hugging Face Spaces.
"""

import logging
import subprocess
import time
import uuid
from typing import Any, Optional, Tuple

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from config import settings
from models import SREAction, SREObservation, SREState
from rewards import RewardCalculator
from security import CommandSanitizer

logger = logging.getLogger(__name__)

# ── Valid Scenarios and Ticket Contexts ────────────────────────────────────
VALID_TASKS = {"easy", "medium", "hard", "dns", "firewall", "permissions", "resource", "cascade"}

TICKET_CONTEXTS = {
    "easy": "Ticket: Investigate why nginx is unresponsive on port 80 and restore service.",
    "medium": "Ticket: Nginx fails to start. Check error logs and correct the configuration.",
    "hard": "Ticket: High disk usage observed. Database connection is refused. Fix backend and clean up disk space.",
    "dns": "Ticket: DNS resolution is completely broken. Applications cannot resolve any hostnames. Restore DNS functionality.",
    "firewall": "Ticket: Web server is running but external connections on ports 80/443 are being refused. Investigate firewall rules and restore access.",
    "permissions": "Ticket: Nginx is running but returning 403 Forbidden. Web root and config permissions appear to be incorrect. Fix permissions and restore service.",
    "resource": "Ticket: Server is extremely slow. /tmp is nearly full and rogue processes are consuming CPU. Clean up resources and restore performance.",
    "cascade": "Ticket: CRITICAL — Multiple failures detected. Nginx upstream backend is unreachable, PostgreSQL rejects all connections, and cron is flooding logs. Resolve all issues.",
}

MAX_REWARD = {
    "easy": 1.0,
    "medium": 1.0,
    "hard": 2.0,
    "dns": 1.0,
    "firewall": 1.0,
    "permissions": 1.0,
    "resource": 1.5,
    "cascade": 2.5,
}


def run_local(cmd: str, timeout: int = 10) -> Tuple[int, str, str]:
    """Helper to run a bash command locally and return exit_code, stdout, stderr."""
    try:
        proc = subprocess.run(
            ["/bin/bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


class SREEnvironment(Environment[SREAction, SREObservation, SREState]):
    """
    Subprocess-based sandbox that breaks the local container infrastructure.
    Safe for HF Spaces. Integrates CommandSanitizer for security and
    RewardCalculator for dense reward signals.
    """

    # We support only one session concurrently altering the system files.
    SUPPORTS_CONCURRENT_SESSIONS = False

    def __init__(self) -> None:
        super().__init__()
        self._state = SREState()
        self.sanitizer = CommandSanitizer()
        self.reward_calc = RewardCalculator()
        self._current_pwd = "/"

    # ── OpenEnv Interface ─────────────────────────────────────────────────

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SREObservation:
        """Reset the sandbox by clearing local system state and applying sabotage."""
        task = kwargs.get("task", "easy")
        if task not in VALID_TASKS:
            raise ValueError(
                f"Invalid task '{task}'. Must be one of: {', '.join(sorted(VALID_TASKS))}"
            )

        self._cleanup_system_state()

        ep_id = episode_id or str(uuid.uuid4())
        self._state = SREState(
            episode_id=ep_id,
            step_count=0,
            current_task=task,
            total_reward=0.0,
            done=False,
            success=False,
        )
        self._current_pwd = "/"

        logger.info("Starting local scenario: %s (episode: %s)", task, ep_id)

        # Apply sabotage
        script = f"/app/scripts/scenario_{task}.sh"
        exit_code, stdout, stderr = run_local(script)

        return SREObservation(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            current_directory=self._current_pwd,
            ticket_context=TICKET_CONTEXTS.get(task, "Fix the broken environment."),
            reward=None,
            done=False,
        )

    def step(
        self,
        action: SREAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> SREObservation:
        """Execute agent action and return observation with reward."""
        self._state.step_count += 1
        
        # ── Security Gate ─────────────────────────────────────────────────
        allowed, reason = self.sanitizer.check(action.command)
        if not allowed:
            penalty = float(settings.penalty_blocked_cmd)
            self._state.total_reward += penalty
            return SREObservation(
                stdout="",
                stderr=f"SECURITY: {reason}",
                exit_code=126,
                current_directory=self._current_pwd,
                last_action_error=reason,
                reward=penalty,
                done=False,
            )

        # ── Execute Command ───────────────────────────────────────────────
        # Maintain PWD across steps by wrapping command
        wrapped_cmd = f"cd {self._current_pwd} && {action.command}; EX=$?; pwd; exit $EX"
        exit_code, raw_stdout, stderr = run_local(wrapped_cmd, timeout=int(timeout_s or 15))

        # Extract working directory from the end of stdout
        stdout = ""
        if raw_stdout:
            lines = raw_stdout.strip().split("\n")
            if lines and lines[-1].startswith("/"):
                self._current_pwd = lines[-1]
                stdout = "\n".join(lines[:-1]) + "\n" if len(lines) > 1 else ""
            else:
                stdout = raw_stdout

        # ── Reward ────────────────────────────────────────────────────────
        reward_result = self.reward_calc.calculate(action.command, action.phase)
        step_reward = reward_result.total
        done = reward_result.done
        success = False

        # Health check
        if not done:
            is_done, is_success, health_reward = self._check_health()
            done = is_done
            success = is_success
            step_reward += health_reward

        self._state.total_reward += step_reward
        self._state.done = done
        self._state.success = success

        return SREObservation(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            current_directory=self._current_pwd,
            reward=step_reward,
            done=done,
            metadata={"success": success, "blocked": False},
        )

    @property
    def state(self) -> SREState:
        """Get the current environment state."""
        return self._state

    def close(self) -> None:
        """Cleanup environment files natively."""
        self._cleanup_system_state()
        logger.info("Local environment closed and cleaned.")

    def get_metadata(self) -> EnvironmentMetadata:
        """Return environment metadata."""
        return EnvironmentMetadata(
            name="SRE-Sandbox",
            description=(
                "Autonomous SRE sandbox natively deployed on Hugging Face Spaces. "
                "Deliberately breaks internal configuration for LLM agents to fix via bash."
            ),
            version="2.0.0",
            author="mohammed-mutee",
        )

    def get_normalized_score(self) -> float:
        """Return the final score normalised to 0.0–1.0."""
        task = self._state.current_task or "easy"
        max_r = MAX_REWARD.get(task, 1.0)
        raw = self._state.total_reward
        return max(0.0, min(1.0, raw / max_r))

    # ── Private Native Handlers ───────────────────────────────────────────

    def _cleanup_system_state(self) -> None:
        """Restores `/etc/nginx` and kills rogue processes natively."""
        cleanup_cmds = [
            "service nginx stop || true",
            "rm -rf /etc/nginx && cp -a /etc/nginx.bak /etc/nginx || true",
            "cp /etc/resolv.conf.bak /etc/resolv.conf 2>/dev/null || true",
            "iptables -F || true",
            "rm -rf /tmp/junk* || true",
            "pkill -f 'dd if=/dev/zero' || true",
            "chown -R www-data:www-data /var/www/html || true",
            "service nginx start || true",
            "service postgresql start || true",
        ]
        cleanup_script = "\n".join(cleanup_cmds)
        run_local(cleanup_script, timeout=10)

    def _check_health(self) -> Tuple[bool, bool, float]:
        """Run health checks on local processes."""
        task = self._state.current_task
        if task in ("dns", "resource"):
            return self._check_scenario_specific()

        # Nginx check
        c_code, c_out, _ = run_local("curl -s -o /dev/null -w \"%{http_code}\" http://localhost")
        nginx_ok = (c_code == 0 and c_out.strip() == "200")
        
        if not nginx_ok:
            return False, False, 0.0

        if task in ("hard", "cascade"):
            # DB check
            db_code, _, _ = run_local("sudo -u postgres psql -c 'SELECT 1'")
            if db_code != 0:
                return False, False, 0.0

        return True, True, settings.reward_task_solved

    def _check_scenario_specific(self) -> Tuple[bool, bool, float]:
        task = self._state.current_task
        if task == "dns":
            code, _, _ = run_local("cat /etc/resolv.conf | grep -q nameserver")
            if code == 0:
                return True, True, settings.reward_task_solved
            return False, False, 0.0

        if task == "resource":
            code, out, _ = run_local("df /tmp --output=pcent | tail -1 | tr -d ' %'")
            if code == 0 and out:
                try:
                    usage = int(out.strip())
                    if usage < 90:
                        return True, True, settings.reward_task_solved
                except ValueError:
                    pass
        return False, False, 0.0
