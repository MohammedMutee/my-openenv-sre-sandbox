"""Tests for the RewardCalculator."""

import pytest

from rewards import RewardCalculator
from config import settings


@pytest.fixture
def calc():
    return RewardCalculator()


class TestDiagnosticRewards:
    """Commands that should earn diagnostic rewards."""

    @pytest.mark.parametrize("cmd", [
        "cat /var/log/nginx/error.log",
        "tail -n 50 /var/log/nginx/error.log",
        "less /var/log/nginx/error.log",
        "head -20 /var/log/nginx/error.log",
        "grep 'error' /var/log/nginx/error.log",
        "journalctl -u nginx",
        "nginx -t",
        "systemctl status nginx",
        "service nginx status",
        "ss -tulnp",
        "netstat -tlnp",
        "df -h",
        "du -sh /var/log",
        "free -m",
        "ps aux",
    ])
    def test_diagnostic_commands_rewarded(self, calc, cmd):
        result = calc.calculate(cmd, phase="research")
        assert result.total > 0, f"Expected reward for diagnostic: {cmd}"

    def test_research_phase_bonus(self, calc):
        result = calc.calculate("cat /var/log/nginx/error.log", phase="research")
        # Should get base + phase bonus
        expected_min = settings.reward_log_investigation + settings.reward_phase_bonus
        assert result.total >= expected_min

    def test_no_phase_bonus_in_execute(self, calc):
        result = calc.calculate("cat /var/log/nginx/error.log", phase="execute")
        # Should get base but no phase bonus
        assert result.total == settings.reward_log_investigation


class TestRemediationRewards:
    """Commands that should earn remediation rewards."""

    @pytest.mark.parametrize("cmd", [
        "service nginx restart",
        "systemctl restart postgresql",
        "nginx -s reload",
        "sed -i 's/foo/bar/' /etc/nginx/nginx.conf",
        "chmod 644 /etc/nginx/nginx.conf",
        "chown www-data:www-data /var/www/html",
        "iptables -D INPUT 1",
        "iptables -F",
    ])
    def test_remediation_commands_rewarded(self, calc, cmd):
        result = calc.calculate(cmd, phase="execute")
        assert result.total > 0, f"Expected reward for remediation: {cmd}"


class TestDestructivePenalty:
    def test_rm_rf_penalty(self, calc):
        result = calc.calculate("rm -rf /var/log", phase="execute")
        assert result.total < 0
        assert result.done is True
        assert result.destructive is True

    def test_penalty_value(self, calc):
        result = calc.calculate("rm -rf /etc", phase="execute")
        assert result.total == settings.penalty_destructive_cmd


class TestNeutralCommands:
    """Commands with no specific reward or penalty."""

    @pytest.mark.parametrize("cmd", [
        "echo hello",
        "pwd",
        "ls -la",
        "whoami",
        "date",
    ])
    def test_neutral_commands_zero_reward(self, calc, cmd):
        result = calc.calculate(cmd, phase="research")
        assert result.total == 0.0
        assert result.done is False
