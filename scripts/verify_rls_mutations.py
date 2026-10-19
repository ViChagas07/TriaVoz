"""Prove that the RLS suite is a real gate, not decoration.

For each mutation:
  1. apply it as the owner (or superuser for role attributes),
  2. run the specific guard/isolation test and require it to FAIL for the expected reason,
  3. restore the original state in a `finally` block,
  4. run the test again and require it to PASS.

Requires the same env vars as `apps/api/tests/conftest.py`:
  TRIAVOZ_TEST_OWNER_DSN, TRIAVOZ_TEST_APP_DSN, TRIAVOZ_TEST_OPS_DSN
and, only for the BYPASSRLS mutation:
  TRIAVOZ_TEST_SUPERUSER_DSN   (postgres superuser; never used by the app)

Run from the repo root:
  cd apps/api && poetry run python ../../scripts/verify_rls_mutations.py
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"

POLICY_RESTORE = (
    "ALTER POLICY tenant_isolation ON appointments "
    "USING (clinic_id = app_current_clinic_id()) "
    "WITH CHECK (clinic_id = app_current_clinic_id())"
)


@dataclass(frozen=True)
class Mutation:
    name: str
    dsn_env: str
    apply_sql: str
    restore_sql: str
    test: str
    expected_failure: str


MUTATIONS = (
    Mutation(
        name="permissive tenant policy",
        dsn_env="TRIAVOZ_TEST_OWNER_DSN",
        apply_sql=(
            "ALTER POLICY tenant_isolation ON appointments "
            "USING (true) WITH CHECK (true)"
        ),
        restore_sql=POLICY_RESTORE,
        test=(
            "tests/isolation/test_rls_isolation.py"
            "::test_each_tenant_sees_only_its_own_rows_in_every_table"
        ),
        expected_failure="LEAK",
    ),
    Mutation(
        name="NO FORCE ROW LEVEL SECURITY",
        dsn_env="TRIAVOZ_TEST_OWNER_DSN",
        apply_sql="ALTER TABLE appointments NO FORCE ROW LEVEL SECURITY",
        restore_sql="ALTER TABLE appointments FORCE ROW LEVEL SECURITY",
        test="tests/isolation/test_rls_guard.py",
        expected_failure="tables without ENABLE+FORCE RLS",
    ),
    Mutation(
        name="BYPASSRLS on the runtime role",
        dsn_env="TRIAVOZ_TEST_SUPERUSER_DSN",
        apply_sql="ALTER ROLE triavoz_app BYPASSRLS",
        restore_sql="ALTER ROLE triavoz_app NOBYPASSRLS",
        test=(
            "tests/isolation/test_rls_isolation.py::test_runtime_role_is_unprivileged"
        ),
        expected_failure="rolbypassrls",
    ),
)


def pytest_run(test: str) -> tuple[int, str]:
    env = os.environ.copy()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", test],
        cwd=API,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, (result.stdout + result.stderr).strip()


def require_env() -> None:
    missing = [
        name
        for name in ("TRIAVOZ_TEST_OWNER_DSN", "TRIAVOZ_TEST_APP_DSN", "TRIAVOZ_TEST_OPS_DSN")
        if not os.environ.get(name)
    ]
    if missing:
        raise SystemExit(f"missing env vars: {', '.join(missing)} (see tests/conftest.py)")


async def mutate(mutation: Mutation, sql: str) -> None:
    dsn = os.environ.get(mutation.dsn_env)
    if not dsn:
        raise RuntimeError(f"{mutation.dsn_env} is not set")
    conn = await asyncpg.connect(dsn)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


def main() -> int:
    require_env()
    failures: list[str] = []

    for mutation in MUTATIONS:
        print(f"\n[{mutation.name}] baseline")
        code, output = pytest_run(mutation.test)
        if code != 0:
            print(output)
            failures.append(f"{mutation.name}: baseline test is not green")
            continue

        if mutation.name.startswith("BYPASSRLS") and not os.environ.get(mutation.dsn_env):
            print(f"SKIP: {mutation.dsn_env} not set (needed to alter the runtime role)")
            continue

        print(f"[{mutation.name}] applying mutation")
        applied = False
        try:
            asyncio.run(mutate(mutation, mutation.apply_sql))
            applied = True
            code, output = pytest_run(mutation.test)
            if code == 0:
                failures.append(f"{mutation.name}: mutation ESCAPED (suite stayed green)")
                print("MUTATION ESCAPED")
            elif mutation.expected_failure not in output:
                failures.append(
                    f"{mutation.name}: suite failed but not for the expected reason"
                )
                print(output)
            else:
                print("detected: suite failed as expected")
        finally:
            if applied:
                asyncio.run(mutate(mutation, mutation.restore_sql))
                print(f"[{mutation.name}] restored")

        if applied:
            code, output = pytest_run(mutation.test)
            if code != 0:
                print(output)
                failures.append(f"{mutation.name}: test still fails after restore")
            else:
                print(f"[{mutation.name}] restore verified: test green again")

    if failures:
        print("\nFAILED:")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("\nAll RLS mutations were detected and restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
