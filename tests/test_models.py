"""Tests for Pydantic models (SREAction, SREObservation, SREState)."""

import pytest
from pydantic import ValidationError

from models import SREAction, SREObservation, SREState


class TestSREAction:
    def test_valid_phases(self):
        for phase in ("research", "plan", "execute", "verify"):
            action = SREAction(phase=phase, command="echo hi", rationale="test")
            assert action.phase == phase

    def test_missing_command_rejected(self):
        with pytest.raises(ValidationError):
            SREAction(phase="execute", rationale="test")

    def test_missing_rationale_rejected(self):
        with pytest.raises(ValidationError):
            SREAction(phase="execute", command="echo hi")

    def test_json_serialization(self, sample_action):
        data = sample_action.model_dump()
        assert data["phase"] == "execute"
        assert data["command"] == "service nginx restart"
        restored = SREAction(**data)
        assert restored.phase == sample_action.phase
        assert restored.command == sample_action.command

    def test_json_schema_has_title(self):
        schema = SREAction.model_json_schema()
        assert schema.get("title") == "SRE Action"

    def test_inherits_metadata(self):
        action = SREAction(phase="execute", command="echo hi", rationale="test")
        assert hasattr(action, "metadata")
        assert isinstance(action.metadata, dict)


class TestSREObservation:
    def test_defaults(self):
        obs = SREObservation(exit_code=0)
        assert obs.stdout == ""
        assert obs.stderr == ""
        assert obs.current_directory == "/"
        assert obs.ticket_context is None
        assert obs.reward is None
        assert obs.done is False  # OpenEnv base default

    def test_with_all_fields(self, sample_observation):
        assert sample_observation.exit_code == 0
        assert "nginx" in sample_observation.stdout
        assert sample_observation.ticket_context is not None

    def test_json_roundtrip(self, sample_observation):
        json_str = sample_observation.model_dump_json()
        restored = SREObservation.model_validate_json(json_str)
        assert restored.exit_code == sample_observation.exit_code
        assert restored.stdout == sample_observation.stdout

    def test_json_schema_has_title(self):
        schema = SREObservation.model_json_schema()
        assert schema.get("title") == "SRE Observation"

    def test_reward_and_done(self):
        obs = SREObservation(exit_code=0, reward=0.5, done=True)
        assert obs.reward == 0.5
        assert obs.done is True


class TestSREState:
    def test_defaults(self):
        state = SREState()
        assert state.step_count == 0
        assert state.total_reward == 0.0
        assert state.done is False
        assert state.success is False

    def test_with_values(self):
        state = SREState(
            episode_id="ep-001",
            step_count=3,
            current_task="easy",
            total_reward=0.9,
            done=True,
            success=True,
        )
        assert state.episode_id == "ep-001"
        assert state.current_task == "easy"
        assert state.total_reward == 0.9
