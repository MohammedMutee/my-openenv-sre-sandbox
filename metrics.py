"""
Persistent metrics collector for SRE Sandbox evaluations.

Saves per-run results as JSON files in the ``results/`` directory and
provides aggregated reporting across multiple runs.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class StepRecord:
    """Record of a single step within a scenario run."""

    step: int
    phase: str
    command: str
    rationale: str
    reward: float
    exit_code: int
    blocked: bool = False
    block_reason: str = ""


@dataclass
class ScenarioResult:
    """Result of a single scenario evaluation."""

    scenario: str
    success: bool
    total_reward: float
    steps: int
    duration_seconds: float
    step_records: list[StepRecord] = field(default_factory=list)
    error: str | None = None


@dataclass
class EvaluationRun:
    """Complete evaluation run across all scenarios."""

    run_id: str
    timestamp: str
    agent_type: str
    scenarios: list[ScenarioResult] = field(default_factory=list)

    @property
    def overall_success_rate(self) -> float:
        if not self.scenarios:
            return 0.0
        passed = sum(1 for s in self.scenarios if s.success)
        return passed / len(self.scenarios)

    @property
    def total_reward(self) -> float:
        return sum(s.total_reward for s in self.scenarios)


class MetricsCollector:
    """
    Collects metrics during an evaluation run and persists them as JSON.
    """

    def __init__(self, agent_type: str = "mock") -> None:
        self.results_dir = settings.results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.run = EvaluationRun(
            run_id=f"run-{int(time.time())}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_type=agent_type,
        )
        self._current_scenario: ScenarioResult | None = None
        self._scenario_start: float = 0.0

    def start_scenario(self, scenario: str) -> None:
        """Begin tracking a new scenario."""
        self._scenario_start = time.time()
        self._current_scenario = ScenarioResult(
            scenario=scenario,
            success=False,
            total_reward=0.0,
            steps=0,
            duration_seconds=0.0,
        )

    def record_step(
        self,
        step: int,
        phase: str,
        command: str,
        rationale: str,
        reward: float,
        exit_code: int,
        blocked: bool = False,
        block_reason: str = "",
    ) -> None:
        """Record a single step within the current scenario."""
        if self._current_scenario is None:
            return

        self._current_scenario.step_records.append(
            StepRecord(
                step=step,
                phase=phase,
                command=command,
                rationale=rationale,
                reward=reward,
                exit_code=exit_code,
                blocked=blocked,
                block_reason=block_reason,
            )
        )
        self._current_scenario.total_reward += reward
        self._current_scenario.steps = step

    def end_scenario(self, success: bool, error: str | None = None) -> None:
        """Finalise the current scenario with success/failure status."""
        if self._current_scenario is None:
            return

        self._current_scenario.success = success
        self._current_scenario.duration_seconds = round(time.time() - self._scenario_start, 2)
        self._current_scenario.error = error
        self.run.scenarios.append(self._current_scenario)
        self._current_scenario = None

    def save(self) -> Path:
        """Persist the full run to a JSON file and return the path."""
        filepath = self.results_dir / f"{self.run.run_id}.json"
        filepath.write_text(
            json.dumps(asdict(self.run), indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Metrics saved to %s", filepath)
        return filepath


class MetricsReporter:
    """
    Generates aggregate statistics across multiple evaluation runs.
    """

    def __init__(self, results_dir: Path | None = None) -> None:
        self.results_dir = results_dir or settings.results_dir

    def load_all_runs(self) -> list[dict]:
        """Load all JSON run files from the results directory."""
        if not self.results_dir.exists():
            return []

        runs = []
        for filepath in sorted(self.results_dir.glob("run-*.json")):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                runs.append(data)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load %s: %s", filepath, exc)
        return runs

    def summary(self) -> dict:
        """
        Generate aggregate stats across all runs.

        Returns:
            Dict with overall stats, per-scenario breakdown, and trends.
        """
        runs = self.load_all_runs()
        if not runs:
            return {"total_runs": 0, "message": "No evaluation runs found."}

        total_runs = len(runs)
        all_scenarios: dict[str, list[dict]] = {}

        for run in runs:
            for scenario in run.get("scenarios", []):
                name = scenario["scenario"]
                all_scenarios.setdefault(name, []).append(scenario)

        scenario_stats = {}
        for name, results in all_scenarios.items():
            successes = sum(1 for r in results if r["success"])
            rewards = [r["total_reward"] for r in results]
            steps = [r["steps"] for r in results]
            durations = [r["duration_seconds"] for r in results]

            scenario_stats[name] = {
                "attempts": len(results),
                "successes": successes,
                "success_rate": round(successes / len(results), 2) if results else 0,
                "avg_reward": round(sum(rewards) / len(rewards), 2) if rewards else 0,
                "avg_steps": round(sum(steps) / len(steps), 1) if steps else 0,
                "avg_duration": round(sum(durations) / len(durations), 1) if durations else 0,
            }

        return {
            "total_runs": total_runs,
            "scenarios": scenario_stats,
            "latest_run": runs[-1].get("timestamp", "unknown"),
        }
