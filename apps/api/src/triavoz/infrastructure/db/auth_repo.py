from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from triavoz.application.auth.ports import RefreshRecord, UserRecord


def _user(row: object) -> UserRecord:
    m = row._mapping  # type: ignore[attr-defined]
    return UserRecord(
        m["id"],
        m["clinic_id"],
        str(m["email"]),
        m["full_name"],
        m["role"],
        m["is_active"],
        m["password_hash"],
    )


class PgAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def find_user_by_email(self, email: str) -> UserRecord | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT id, clinic_id, email, full_name, role, is_active, password_hash "
                    "FROM clinic_users WHERE email = :email"
                ),
                {"email": email},
            )
        ).first()
        return _user(row) if row else None

    async def get_user(self, user_id: UUID) -> UserRecord | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT id, clinic_id, email, full_name, role, is_active, password_hash "
                    "FROM clinic_users WHERE id = :id"
                ),
                {"id": user_id},
            )
        ).first()
        return _user(row) if row else None

    async def create_refresh(
        self,
        *,
        clinic_id: UUID,
        user_id: UUID,
        family_id: UUID,
        token_hash: bytes,
        expires_at: datetime,
        created_ip: str | None,
        user_agent: str | None,
    ) -> UUID:
        token_id = (
            await self._s.execute(
                text(
                    "INSERT INTO refresh_tokens (clinic_id, user_id, family_id, token_hash, "
                    "expires_at, created_ip, user_agent) "
                    "VALUES (:cid, :uid, :fid, :hash, :exp, :ip, :ua) RETURNING id"
                ),
                {
                    "cid": clinic_id,
                    "uid": user_id,
                    "fid": family_id,
                    "hash": token_hash,
                    "exp": expires_at,
                    "ip": created_ip,
                    "ua": user_agent,
                },
            )
        ).scalar_one()
        return UUID(str(token_id))

    async def find_refresh(self, token_hash: bytes) -> RefreshRecord | None:
        row = (
            await self._s.execute(
                text(
                    "SELECT id, clinic_id, user_id, family_id, token_hash, expires_at, "
                    "revoked_at, revoked_reason FROM refresh_tokens WHERE token_hash = :hash"
                ),
                {"hash": token_hash},
            )
        ).first()
        if row is None:
            return None
        return RefreshRecord(
            row.id,
            row.clinic_id,
            row.user_id,
            row.family_id,
            bytes(row.token_hash),
            row.expires_at,
            row.revoked_at,
            row.revoked_reason,
        )

    async def revoke_token(
        self, token_id: UUID, reason: str, replaced_by_id: UUID | None = None
    ) -> bool:
        result = await self._s.execute(
            text(
                "UPDATE refresh_tokens SET revoked_at = now(), revoked_reason = :reason, "
                "replaced_by_id = :replaced WHERE id = :id AND revoked_at IS NULL"
            ),
            {"id": token_id, "reason": reason, "replaced": replaced_by_id},
        )
        # The caller uses the row count as an atomic compare-and-set: exactly one concurrent
        # refresh may rotate a given token.
        return bool(getattr(result, "rowcount", 0) or 0)

    async def revoke_family(self, family_id: UUID, reason: str) -> int:
        result = await self._s.execute(
            text(
                "UPDATE refresh_tokens SET revoked_at = now(), revoked_reason = :reason "
                "WHERE family_id = :fid AND revoked_at IS NULL"
            ),
            {"fid": family_id, "reason": reason},
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def revoke_by_hash(self, token_hash: bytes, reason: str) -> None:
        await self._s.execute(
            text(
                "UPDATE refresh_tokens SET revoked_at = now(), revoked_reason = :reason "
                "WHERE token_hash = :hash AND revoked_at IS NULL"
            ),
            {"hash": token_hash, "reason": reason},
        )

    async def add_audit(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None,
        user_id: UUID | None,
        ip: str | None,
    ) -> None:
        await self._s.execute(
            text(
                "INSERT INTO audit_log "
                "(clinic_id, user_id, action, resource_type, resource_id, ip) "
                "VALUES (app_current_clinic_id(), :uid, :action, :rtype, :rid, :ip)"
            ),
            {
                "uid": user_id,
                "action": action,
                "rtype": resource_type,
                "rid": resource_id,
                "ip": ip,
            },
        )
