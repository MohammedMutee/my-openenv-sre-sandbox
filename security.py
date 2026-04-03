"""
Command security sandbox for the SRE environment.

Validates agent commands against a blocklist of dangerous patterns
before execution. Blocked commands receive an instant penalty without
being run inside the container.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Blocked Patterns ──────────────────────────────────────────────────────
# Each tuple: (compiled regex, human-readable description)
_BLOCKED_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"rm\s+(-[a-zA-Z]*)?r[a-zA-Z]*\s+/(?:\s|$)"), "recursive delete on root"),
    (re.compile(r"rm\s+(-[a-zA-Z]*)?rf\s"), "force-recursive delete"),
    (re.compile(r"mkfs\b"), "filesystem format"),
    (re.compile(r"dd\s+.*if=.*/dev/"), "raw device write via dd"),
    (re.compile(r">\s*/dev/sd[a-z]"), "overwrite block device"),
    (re.compile(r":\(\)\s*\{.*\|.*&\s*\}\s*;"), "fork bomb"),
    (re.compile(r"\bshutdown\b"), "system shutdown"),
    (re.compile(r"\breboot\b"), "system reboot"),
    (re.compile(r"\bhalt\b"), "system halt"),
    (re.compile(r"\binit\s+0\b"), "init shutdown"),
    (re.compile(r"chmod\s+(-[a-zA-Z]*)?\s*777\s+/"), "dangerous chmod on root paths"),
    (re.compile(r"chown\s+.*\s+/etc/shadow"), "shadow file ownership change"),
    (re.compile(r">\s*/etc/passwd"), "overwrite passwd"),
    (re.compile(r">\s*/etc/shadow"), "overwrite shadow"),
    (re.compile(r"curl\s+.*\|\s*(ba)?sh"), "pipe-to-shell execution"),
    (re.compile(r"wget\s+.*\|\s*(ba)?sh"), "pipe-to-shell execution"),
    (re.compile(r"python[23]?\s+-c\s+.*import\s+os.*system"), "python os.system escape"),
]

# ── Safe Overrides ────────────────────────────────────────────────────────
# Patterns that look dangerous but are actually safe in context
_SAFE_OVERRIDES: list[re.Pattern] = [
    re.compile(r"rm\s+-f\s+/var/log/"),          # Cleaning log files is expected
    re.compile(r"rm\s+-f\s+/tmp/"),               # Cleaning tmp is fine
    re.compile(r"rm\s+/var/log/"),                 # Single file log removal
]


class CommandSanitizer:
    """
    Validates commands against security policies before container execution.

    Usage::

        sanitizer = CommandSanitizer()
        allowed, reason = sanitizer.check("rm -rf /")
        if not allowed:
            print(f"BLOCKED: {reason}")
    """

    def __init__(
        self,
        blocked_patterns: list[tuple[re.Pattern, str]] | None = None,
        safe_overrides: list[re.Pattern] | None = None,
    ) -> None:
        self.blocked_patterns = blocked_patterns or _BLOCKED_PATTERNS
        self.safe_overrides = safe_overrides or _SAFE_OVERRIDES

    def check(self, command: str) -> tuple[bool, str]:
        """
        Check whether a command is safe to execute.

        Args:
            command: The bash command string to validate.

        Returns:
            A tuple of ``(allowed, reason)``. If blocked, *reason*
            describes why.
        """
        # Check safe overrides first
        for safe_pattern in self.safe_overrides:
            if safe_pattern.search(command):
                return True, "matched safe override"

        # Check against blocklist
        for pattern, description in self.blocked_patterns:
            if pattern.search(command):
                logger.warning(
                    "BLOCKED command — %s: %s", description, command
                )
                return False, f"Command blocked: {description}"

        return True, "ok"
