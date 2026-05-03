"""Scenario result records for visible acceptance execution."""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ScenarioStatus = Literal["passed", "failed", "error", "skipped"]
FailureType = Literal[
    "scenario_failure",
    "step_error",
    "product_error",
    "harness_error",
]


class ScenarioFailureError(AssertionError):
    """Visible scenario assertion failed."""


class ProductError(RuntimeError):
    """The product under test failed before satisfying the scenario."""


class HarnessError(RuntimeError):
    """The acceptance harness failed independently of product behavior."""


@dataclass(frozen=True)
class ScenarioResult:
    schema_version: int
    run_id: str
    problem_id: str
    checkpoint_id: str
    scenario_id: str
    feature_path: str
    scenario_name: str
    tags: list[str]
    status: ScenarioStatus
    failure_type: FailureType | None
    duration_ms: float
    stdout_path: str | None
    stderr_path: str | None

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)


def write_jsonl(path: Path, rows: list[ScenarioResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(row.to_json())
            handle.write("\n")
