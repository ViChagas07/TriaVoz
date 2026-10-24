"""Contract snapshot for the HMAC-protected API used by the voice worker.

The snapshot intentionally covers only `/internal/agent/*` and the component schemas those routes
reference. Any request/response rename or type change now fails CI; updating the snapshot is an
explicit, reviewable act (`UPDATE_CONTRACT_SNAPSHOTS=1 pytest tests/contracts`).
"""

from __future__ import annotations

import difflib
import json
import os
from pathlib import Path
from typing import Any

from triavoz.main import create_app

SNAPSHOT = Path(__file__).parent / "snapshots" / "internal_agent_openapi.json"


def _refs(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[-1])
        for value in node.values():
            found |= _refs(value)
    elif isinstance(node, list):
        for value in node:
            found |= _refs(value)
    return found


def _contract() -> dict[str, Any]:
    schema = create_app().openapi()
    paths = {
        path: operations
        for path, operations in schema["paths"].items()
        if path.startswith("/internal/agent")
    }
    assert paths, "internal agent routes disappeared from OpenAPI"
    all_schemas = schema.get("components", {}).get("schemas", {})
    pending = _refs(paths)
    used: set[str] = set()
    while pending:
        name = pending.pop()
        if name in used:
            continue
        used.add(name)
        pending |= _refs(all_schemas[name])
    return {
        "paths": paths,
        "components": {"schemas": {name: all_schemas[name] for name in sorted(used)}},
    }


def test_internal_agent_contract_matches_snapshot() -> None:
    actual = _contract()
    rendered = json.dumps(actual, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("UPDATE_CONTRACT_SNAPSHOTS") == "1":
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(rendered, encoding="utf-8")
        return
    assert SNAPSHOT.exists(), f"missing contract snapshot: {SNAPSHOT}"
    expected = SNAPSHOT.read_text(encoding="utf-8")
    if actual != json.loads(expected):
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                rendered.splitlines(),
                fromfile="snapshot",
                tofile="current",
                lineterm="",
            )
        )
        raise AssertionError(
            "internal agent contract drifted; review the diff and update "
            f"the snapshot intentionally:\n{diff}"
        )


def test_every_internal_operation_declares_a_json_response_schema() -> None:
    contract = _contract()
    missing: list[str] = []
    for path, operations in contract["paths"].items():
        for method, operation in operations.items():
            schema = (
                operation.get("responses", {})
                .get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            if not schema or not ("$ref" in schema or "$ref" in schema.get("items", {})):
                missing.append(f"{method.upper()} {path}")
    assert not missing, f"internal routes without an explicit response model: {missing}"
