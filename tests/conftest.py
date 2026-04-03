"""Shared pytest fixtures for the SRE Sandbox test suite."""

import pytest

from models import SREAction, SREObservation


@pytest.fixture
def sample_action():
    """A sample SREAction for testing."""
    return SREAction(
        phase="execute",
        command="service nginx restart",
        rationale="Restarting nginx to restore service.",
    )


@pytest.fixture
def sample_observation():
    """A sample SREObservation for testing."""
    return SREObservation(
        stdout="nginx: started\n",
        stderr="",
        exit_code=0,
        current_directory="/",
        ticket_context="Ticket: Nginx is down.",
    )


@pytest.fixture
def diagnostic_action():
    """An action that should trigger diagnostic reward."""
    return SREAction(
        phase="research",
        command="cat /var/log/nginx/error.log",
        rationale="Checking error logs.",
    )


@pytest.fixture
def destructive_action():
    """An action that should be penalised."""
    return SREAction(
        phase="execute",
        command="rm -rf /",
        rationale="Bad idea.",
    )
