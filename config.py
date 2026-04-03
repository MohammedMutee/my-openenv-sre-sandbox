"""
Centralised configuration for the SRE Sandbox.

Loads settings from environment variables and ``.env`` files using
pydantic-settings. Every tunable parameter lives here.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── LLM ───────────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Docker ────────────────────────────────────────────────────────────
    docker_image: str = "sre-sandbox"
    container_startup_wait: float = 2.0

    # ── Evaluation ────────────────────────────────────────────────────────
    max_steps: int = 10
    agent_type: str = "mock"  # "mock" or "gemini"

    # ── Reward Weights ────────────────────────────────────────────────────
    reward_log_investigation: float = 0.2
    reward_service_restart: float = 0.3
    reward_task_solved: float = 0.5
    reward_phase_bonus: float = 0.1
    penalty_destructive_cmd: float = -1.0
    penalty_blocked_cmd: float = -0.5

    # ── Paths ─────────────────────────────────────────────────────────────
    results_dir: Path = Path("results")


# Singleton — import this everywhere
settings = Settings()
