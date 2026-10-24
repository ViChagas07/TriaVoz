from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class ToolEvent:
    name: str
    ok: bool
    arguments: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    output: Any = None


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class ScenarioResult:
    scenario: str
    description: str
    task_success: bool
    hallucinated_slots: int
    tool_errors: int
    tool_calls: int
    tool_error_recovery: bool | None
    handoff_correct: bool
    expected_handoff: bool
    actual_handoff: bool
    turns_to_completion: int
    duration_ms: float
    checks: list[Check] = field(default_factory=list)
    tool_events: list[ToolEvent] = field(default_factory=list)
    transcript: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SuiteResult:
    suite: str
    started_at: str
    database: str
    scenarios: list[ScenarioResult]

    @property
    def total(self) -> int:
        return len(self.scenarios)

    @property
    def successful(self) -> int:
        return sum(1 for s in self.scenarios if s.task_success)

    @property
    def hallucinated_slots(self) -> int:
        return sum(s.hallucinated_slots for s in self.scenarios)

    @property
    def tool_errors(self) -> int:
        return sum(s.tool_errors for s in self.scenarios)

    @property
    def handoff_accuracy(self) -> float:
        if not self.scenarios:
            return 1.0
        return sum(1 for s in self.scenarios if s.handoff_correct) / len(self.scenarios)

    @property
    def task_success_rate(self) -> float:
        return self.successful / self.total if self.total else 0.0

    @property
    def no_hallucinated_slot_rate(self) -> float:
        if not self.scenarios:
            return 1.0
        clean = sum(1 for s in self.scenarios if s.hallucinated_slots == 0)
        return clean / len(self.scenarios)

    @property
    def tool_error_recovery_rate(self) -> float | None:
        applicable = [s for s in self.scenarios if s.tool_error_recovery is not None]
        if not applicable:
            return None
        return sum(1 for s in applicable if s.tool_error_recovery) / len(applicable)

    @property
    def average_turns(self) -> float:
        return (
            sum(s.turns_to_completion for s in self.scenarios) / self.total if self.total else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "started_at": self.started_at,
            "database": self.database,
            "aggregate": {
                "total": self.total,
                "successful": self.successful,
                "task_success_rate": round(self.task_success_rate, 4),
                "hallucinated_slots": self.hallucinated_slots,
                "no_hallucinated_slot_rate": round(self.no_hallucinated_slot_rate, 4),
                "tool_errors": self.tool_errors,
                "tool_error_recovery_rate": (
                    round(self.tool_error_recovery_rate, 4)
                    if self.tool_error_recovery_rate is not None
                    else None
                ),
                "handoff_accuracy": round(self.handoff_accuracy, 4),
                "average_turns": round(self.average_turns, 2),
            },
            "scenarios": [s.to_dict() for s in self.scenarios],
        }

    def markdown(self) -> str:
        lines = [
            "| Scenario | Success | Hallucinated slots | Tool errors | Recovery | "
            "Handoff | Turns |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for s in self.scenarios:
            recovery = (
                "n/a"
                if s.tool_error_recovery is None
                else ("yes" if s.tool_error_recovery else "no")
            )
            lines.append(
                f"| `{s.scenario}` | {'PASS' if s.task_success else 'FAIL'} | "
                f"{s.hallucinated_slots} | {s.tool_errors} | {recovery} | "
                f"{'yes' if s.handoff_correct else 'no'} | {s.turns_to_completion} |"
            )
        recovery_rate = self.tool_error_recovery_rate
        lines += [
            "",
            f"**Suite:** {self.successful}/{self.total} scenarios passed · "
            f"task success **{self.task_success_rate:.0%}** · "
            f"no-hallucinated-slot **{self.no_hallucinated_slot_rate:.0%}** · "
            f"tool-error recovery "
            f"**{recovery_rate:.0%}** · "
            f"handoff accuracy **{self.handoff_accuracy:.0%}** · "
            f"average **{self.average_turns:.1f}** turns.",
        ]
        return "\n".join(lines)


Speaker = Literal["patient", "agent", "tool"]
