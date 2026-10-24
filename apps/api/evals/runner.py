from __future__ import annotations

import asyncio
import contextlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from evals.fixtures import drop_eval_clinic, eval_phone, seed_eval_clinic
from evals.models import ScenarioResult, SuiteResult
from evals.scenarios import SCENARIOS, Scenario

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _prepare_env() -> None:
    app_dsn = os.environ.get("TRIAVOZ_TEST_APP_DSN")
    if not app_dsn:
        raise SystemExit(
            "TRIAVOZ_TEST_APP_DSN is required (a Postgres DB migrated with Alembic). "
            "See apps/api/tests/conftest.py."
        )
    os.environ["TRIAVOZ_DATABASE_URL_APP"] = app_dsn.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    redis_url = os.environ.get("TRIAVOZ_TEST_REDIS_URL")
    if redis_url:
        os.environ["TRIAVOZ_REDIS_URL"] = redis_url
    os.environ.setdefault("TRIAVOZ_INTERNAL_HMAC_SECRET", "eval-only-hmac-secret")
    os.environ.setdefault("TRIAVOZ_LOG_FORMAT", "plain")
    os.environ.setdefault("TRIAVOZ_ENVIRONMENT", "eval")


def _database_label() -> str:
    dsn = os.environ.get("TRIAVOZ_TEST_APP_DSN", "")
    parsed = urlparse(dsn)
    host = parsed.hostname or "unknown"
    name = (parsed.path or "/triavoz").lstrip("/")
    return f"{host}/{name}"


def _selected(suite: str, only: str | None) -> list[Scenario]:
    scenarios = (
        SCENARIOS
        if suite in {"all", "deterministic"}
        else [s for s in SCENARIOS if s.name == suite]
    )
    if only:
        scenarios = [s for s in scenarios if s.name == only]
    if not scenarios:
        raise SystemExit(f"unknown eval scenario: {only or suite}")
    return scenarios


async def run_suite(*, suite: str = "deterministic", only: str | None = None) -> SuiteResult:
    _prepare_env()
    # Imports happen after the environment is fixed: settings are cached.
    from triavoz_agent.api_client import TriaVozApi

    from triavoz.config import get_settings
    from triavoz.main import create_app

    fixture = await seed_eval_clinic()
    results: list[ScenarioResult] = []
    started_at = datetime.now(UTC).isoformat()
    try:
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://eval") as client:
            api = TriaVozApi(
                "http://eval",
                get_settings().internal_hmac_secret.get_secret_value(),
                client=client,
            )
            for scenario in _selected(suite, only):
                # Imported here so the session uses the same fixture/API instance.
                from evals.session import EvalSession

                session = await EvalSession.open(api, fixture, phone=eval_phone(), channel="phone")
                started = time.perf_counter()
                data = None
                error: str | None = None
                try:
                    data = await scenario.run(session)
                except Exception as exc:  # one bad scenario must not hide the others
                    error = f"{type(exc).__name__}: {exc}"
                finally:
                    with contextlib.suppress(Exception):
                        await session.finish(status="failed", reason="eval_error")
                duration_ms = (time.perf_counter() - started) * 1000
                checks = data.checks if data else []
                success = bool(data and all(c.ok for c in checks) and error is None)
                expected_handoff = data.expected_handoff if data else scenario.expected_handoff
                actual_handoff = data.actual_handoff if data else False
                if error is not None:
                    from evals.models import Check

                    checks = [*checks, Check("no_exception", False, error)]
                results.append(
                    ScenarioResult(
                        scenario=scenario.name,
                        description=scenario.description,
                        task_success=success,
                        hallucinated_slots=session.agent.ledger.hallucinated,
                        tool_errors=session.agent.tools.errors,
                        tool_calls=session.agent.tools.calls,
                        tool_error_recovery=(data.tool_error_recovery if data else None),
                        handoff_correct=expected_handoff == actual_handoff,
                        expected_handoff=expected_handoff,
                        actual_handoff=actual_handoff,
                        turns_to_completion=len(session.agent.transcript),
                        duration_ms=round(duration_ms, 1),
                        checks=checks,
                        tool_events=session.agent.tool_events,
                        transcript=session.agent.transcript,
                        error=error,
                    )
                )
    finally:
        await drop_eval_clinic(fixture.clinic_id)
    return SuiteResult(
        suite=suite,
        started_at=started_at,
        database=_database_label(),
        scenarios=results,
    )


def write_artifacts(
    result: SuiteResult,
    *,
    json_out: Path | None = None,
    markdown_out: Path | None = None,
) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = json_out or RESULTS_DIR / "latest.json"
    markdown_path = markdown_out or RESULTS_DIR / "latest.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(result.markdown() + "\n", encoding="utf-8")
    return json_path, markdown_path


def summarize(result: SuiteResult) -> str:
    aggregate = result.to_dict()["aggregate"]
    return (
        f"{aggregate['successful']}/{aggregate['total']} scenarios passed · "
        f"task success {aggregate['task_success_rate']:.0%} · "
        f"hallucinated slots {aggregate['hallucinated_slots']} · "
        f"no-hallucinated-slot {aggregate['no_hallucinated_slot_rate']:.0%} · "
        f"handoff accuracy {aggregate['handoff_accuracy']:.0%} · "
        f"average {aggregate['average_turns']:.1f} turns"
    )


def verdict(result: SuiteResult) -> int:
    if result.hallucinated_slots:
        return 1
    if result.successful != result.total:
        return 1
    if result.handoff_accuracy < 1.0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="TriaVoz text-mode agent evals")
    parser.add_argument(
        "--suite",
        default="deterministic",
        help="deterministic (all), all, or a single scenario name",
    )
    parser.add_argument("--scenario", default=None, help="run only this scenario")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args(argv)

    result = asyncio.run(run_suite(suite=args.suite, only=args.scenario))
    json_path, markdown_path = write_artifacts(
        result, json_out=args.json_out, markdown_out=args.markdown_out
    )
    print(result.markdown())
    print(f"\n{summarize(result)}")
    print(f"artifacts: {json_path} · {markdown_path}")
    return verdict(result)


if __name__ == "__main__":
    sys.exit(main())
