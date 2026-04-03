"""
Dense reward calculator for the SRE Sandbox.

Uses regex-based pattern matching to award points for diagnostic
and remediation actions, with phase-appropriate bonuses. Much more
robust than simple string-in-string matching.
"""

import logging
import re
from dataclasses import dataclass, field

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class RewardSignal:
    """A single reward event with its value and description."""

    value: float
    reason: str


@dataclass
class RewardResult:
    """Aggregated reward outcome for a single step."""

    total: float = 0.0
    signals: list[RewardSignal] = field(default_factory=list)
    done: bool = False
    destructive: bool = False

    def add(self, value: float, reason: str) -> None:
        self.signals.append(RewardSignal(value=value, reason=reason))
        self.total += value


# ── Diagnostic Patterns (+reward_log_investigation) ───────────────────────
_DIAGNOSTIC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(cat|less|tail|head|more)\b.*\b(error|err)\.log\b"), "read error log"),
    (re.compile(r"\b(cat|less|tail|head|more)\b.*\b(syslog|messages|dmesg)\b"), "read system log"),
    (re.compile(r"\bgrep\b.*\b(error|fail|crit)\b.*\.log\b"), "grep log for errors"),
    (re.compile(r"\bjournalctl\b"), "check journal logs"),
    (re.compile(r"\bnginx\s+-t\b"), "test nginx config"),
    (re.compile(r"\bsystemctl\s+status\b"), "check service status"),
    (re.compile(r"\bservice\s+\S+\s+status\b"), "check service status"),
    (re.compile(r"\bss\s+-[a-z]*l"), "check listening ports"),
    (re.compile(r"\bnetstat\s+-[a-z]*l"), "check listening ports"),
    (re.compile(r"\bdf\s+-"), "check disk usage"),
    (re.compile(r"\bdu\s+-"), "check directory sizes"),
    (re.compile(r"\bfree\s"), "check memory usage"),
    (re.compile(r"\btop\s+-bn"), "check process state"),
    (re.compile(r"\bps\s+aux"), "list processes"),
    (re.compile(r"\blsof\b.*:\d+"), "check port usage"),
]

# ── Remediation Patterns (+reward_service_restart) ────────────────────────
_REMEDIATION_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(service|systemctl)\s+\S*\s*restart\b"), "restart service"),
    (re.compile(r"\b(service|systemctl)\s+\S*\s*start\b"), "start service"),
    (re.compile(r"\bpg_ctl\s+.*start\b"), "start postgres via pg_ctl"),
    (re.compile(r"\bnginx\s+-s\s+reload\b"), "reload nginx"),
    (re.compile(r"\bsed\s+-i\b"), "in-place config edit"),
    (re.compile(r"\biptables\s+-D\b"), "remove firewall rule"),
    (re.compile(r"\biptables\s+-F\b"), "flush firewall rules"),
    (re.compile(r"\bchmod\b.*\b(644|755|600)\b"), "fix file permissions"),
    (re.compile(r"\bchown\b"), "fix file ownership"),
]


class RewardCalculator:
    """
    Calculates dense rewards for agent actions using regex pattern matching.

    Supports phase-appropriate bonuses: diagnostic commands in ``research``
    phase get an extra bonus.
    """

    def __init__(self) -> None:
        self.diagnostic_patterns = _DIAGNOSTIC_PATTERNS
        self.remediation_patterns = _REMEDIATION_PATTERNS

    def calculate(self, command: str, phase: str) -> RewardResult:
        """
        Calculate the reward for a command + phase combination.

        Args:
            command: The bash command the agent ran.
            phase: The GSD phase (``research``, ``plan``, ``execute``, ``verify``).

        Returns:
            A :class:`RewardResult` with all reward signals.
        """
        result = RewardResult()

        # ── Destructive penalty ───────────────────────────────────────────
        if re.search(r"\brm\s+(-[a-zA-Z]*)?rf\s", command):
            result.add(settings.penalty_destructive_cmd, "destructive command (rm -rf)")
            result.done = True
            result.destructive = True
            return result

        # ── Diagnostic rewards ────────────────────────────────────────────
        for pattern, desc in self.diagnostic_patterns:
            if pattern.search(command):
                result.add(settings.reward_log_investigation, f"diagnostic: {desc}")

                # Phase bonus: research phase + diagnostic = extra credit
                if phase == "research":
                    result.add(
                        settings.reward_phase_bonus,
                        f"phase bonus: {desc} during research",
                    )
                break  # Only award once per step

        # ── Remediation rewards ───────────────────────────────────────────
        for pattern, desc in self.remediation_patterns:
            if pattern.search(command):
                result.add(settings.reward_service_restart, f"remediation: {desc}")

                # Phase bonus: execute phase + remediation = extra credit
                if phase == "execute":
                    result.add(
                        settings.reward_phase_bonus,
                        f"phase bonus: {desc} during execute",
                    )
                break  # Only award once per step

        return result
