"""
SRE Sandbox — Typed Pydantic models for the OpenEnv environment.

All models inherit from the openenv-core base types to ensure spec compliance.
"""

from typing import Optional

from pydantic import Field

from openenv.core.env_server.types import Action, Observation, State


class SREAction(Action):
    """An action the SRE agent can take inside the sandbox.

    The agent must specify a GSD workflow phase, a bash command to execute,
    and a rationale explaining the reasoning.
    """

    model_config = {"title": "SRE Action"}

    phase: str = Field(
        description="GSD workflow phase: research, plan, execute, or verify.",
    )
    command: str = Field(
        description="The bash command to run inside the sandbox container.",
    )
    rationale: str = Field(
        description="Why you are running this command based on the current phase.",
    )


class SREObservation(Observation):
    """Observation returned by the SRE environment after each step or reset.

    Inherits ``reward``, ``done``, and ``metadata`` from the OpenEnv
    ``Observation`` base class.
    """

    model_config = {"title": "SRE Observation"}

    stdout: str = Field(default="", description="Standard output from the command.")
    stderr: str = Field(default="", description="Standard error from the command.")
    exit_code: int = Field(default=0, description="Exit code of the command.")
    current_directory: str = Field(
        default="/", description="Working directory after command execution."
    )
    ticket_context: Optional[str] = Field(
        default=None,
        description="The SRE incident ticket (provided on reset, None on step).",
    )
    last_action_error: Optional[str] = Field(
        default=None,
        description="Error message if the last action was blocked or failed.",
    )


class SREState(State):
    """Internal state of the SRE sandbox environment.

    Inherits ``episode_id`` and ``step_count`` from the OpenEnv ``State`` base.
    """

    model_config = {"title": "SRE State"}

    current_task: Optional[str] = Field(
        default=None,
        description="Current sabotage scenario name.",
    )
    total_reward: float = Field(
        default=0.0,
        description="Cumulative reward for the current episode.",
    )
    done: bool = Field(
        default=False,
        description="Whether the current episode has terminated.",
    )
    success: bool = Field(
        default=False,
        description="Whether the agent successfully fixed the environment.",
    )
