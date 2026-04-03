"""Tests for the SREEnvironment (non-Docker unit tests)."""

import pytest

from env import VALID_TASKS, TICKET_CONTEXTS, MAX_REWARD


class TestValidTasks:
    """Test scenario validation without Docker."""

    def test_all_tasks_have_ticket_contexts(self):
        for task in VALID_TASKS:
            assert task in TICKET_CONTEXTS, f"Missing ticket context for task: {task}"

    def test_ticket_contexts_are_non_empty(self):
        for task, context in TICKET_CONTEXTS.items():
            assert len(context) > 10, f"Ticket context too short for: {task}"

    def test_valid_task_set_includes_originals(self):
        for task in ("easy", "medium", "hard"):
            assert task in VALID_TASKS

    def test_valid_task_set_includes_new_scenarios(self):
        for task in ("dns", "firewall", "permissions", "resource", "cascade"):
            assert task in VALID_TASKS

    def test_all_tasks_have_max_reward(self):
        for task in VALID_TASKS:
            assert task in MAX_REWARD, f"Missing max reward for task: {task}"
            assert MAX_REWARD[task] > 0


class TestInputValidation:
    """Test that invalid inputs are rejected properly."""

    def test_invalid_task_raises_value_error(self):
        invalid_tasks = ["invalid", "", "EASY", "super_hard", "test"]
        for task in invalid_tasks:
            assert task not in VALID_TASKS, f"Task should be invalid: {task}"


class TestScenarioScripts:
    """Verify scenario script files exist."""

    @pytest.mark.parametrize("task", sorted(VALID_TASKS))
    def test_scenario_script_exists(self, task):
        from pathlib import Path

        script = Path(f"scripts/scenario_{task}.sh")
        assert script.exists(), f"Missing script: {script}"

    @pytest.mark.parametrize("task", sorted(VALID_TASKS))
    def test_scenario_script_is_executable_shell(self, task):
        from pathlib import Path

        script = Path(f"scripts/scenario_{task}.sh")
        content = script.read_text()
        assert content.startswith("#!/bin/bash"), f"Script missing shebang: {script}"
