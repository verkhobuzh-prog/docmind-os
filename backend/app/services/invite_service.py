"""Pilot invite codes and member tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.core.config import settings
from app.db.supabase import get_supabase, run_supabase
from app.schemas.invite import (
    InviteClaimResponse,
    InviteCodeResponse,
    InviteCreateRequest,
    InviteValidateResponse,
    PilotMemberResponse,
)
from app.utils.invite_codes import generate_invite_code

INVITE_TABLE = "invite_codes"
MEMBERS_TABLE = "pilot_members"


class InviteService:
    def _normalize_code(self, code: str) -> str:
        return code.strip().upper().replace(" ", "")

    async def validate_code(self, code: str) -> InviteValidateResponse:
        normalized = self._normalize_code(code)
        row = await self._fetch_code_row(normalized)
        if row is None:
            return InviteValidateResponse(valid=False, message="Код запрошення не знайдено")
        err = self._code_usable_error(row)
        if err:
            return InviteValidateResponse(valid=False, message=err)
        return InviteValidateResponse(valid=True, label=row.get("label"))

    async def claim_invite(
        self,
        *,
        code: str,
        user_id: str,
        email: str,
        display_name: Optional[str] = None,
    ) -> InviteClaimResponse:
        if not settings.supabase_configured:
            raise HTTPException(status_code=503, detail="Service unavailable")

        existing = await self._get_member(user_id)
        if existing:
            return InviteClaimResponse(ok=True, message="Ви вже підключені до пілоту")

        normalized = self._normalize_code(code)
        row = await self._fetch_code_row(normalized)
        if row is None:
            raise HTTPException(status_code=400, detail="Невірний код запрошення")
        err = self._code_usable_error(row)
        if err:
            raise HTTPException(status_code=400, detail=err)

        if settings.PILOT_INVITE_REQUIRED:
            await self._insert_member(
                user_id=user_id,
                email=email,
                display_name=display_name,
                invite_code_id=str(row["id"]),
                invite_code=normalized,
            )
            await self._increment_use_count(str(row["id"]), int(row.get("use_count") or 0))
        return InviteClaimResponse(ok=True, message="Запрошення прийнято")

    async def is_pilot_member(self, user_id: str) -> bool:
        if not settings.supabase_configured:
            return True
        return (await self._get_member(user_id)) is not None

    async def ensure_pilot_member(self, user: dict[str, Any]) -> None:
        """After login: reject if invite required and user never claimed."""
        if not settings.PILOT_INVITE_REQUIRED or settings.auth_disabled:
            return
        if not settings.supabase_configured:
            return
        member = await self._get_member(str(user["id"]))
        if member:
            return
        email = (user.get("email") or "").lower()
        if email in settings.pilot_admin_emails:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Потрібен код запрошення. Зареєструйтесь за посиланням від адміністратора.",
        )

    async def create_invite(
        self, admin_user: dict[str, Any], body: InviteCreateRequest
    ) -> InviteCodeResponse:
        code = generate_invite_code()
        expires_at = None
        if body.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

        payload = {
            "code": code,
            "label": body.label,
            "created_by": str(admin_user["id"]),
            "max_uses": body.max_uses,
            "use_count": 0,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_active": True,
        }
        client = get_supabase()

        def _insert():
            return client.table(INVITE_TABLE).insert(payload).execute()

        result = await run_supabase(_insert)
        row = result.data[0]
        return self._to_invite_response(row)

    async def list_invites(self) -> list[InviteCodeResponse]:
        client = get_supabase()

        def _q():
            return (
                client.table(INVITE_TABLE)
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )

        result = await run_supabase(_q)
        return [self._to_invite_response(r) for r in result.data or []]

    async def list_members(self) -> list[PilotMemberResponse]:
        client = get_supabase()

        def _q():
            return (
                client.table(MEMBERS_TABLE)
                .select("*")
                .order("joined_at", desc=True)
                .execute()
            )

        result = await run_supabase(_q)
        return [
            PilotMemberResponse(
                id=UUID(str(r["id"])),
                user_id=UUID(str(r["user_id"])),
                email=r["email"],
                display_name=r.get("display_name"),
                invite_code=r.get("invite_code"),
                joined_at=r["joined_at"],
            )
            for r in result.data or []
        ]

    def _to_invite_response(self, row: dict) -> InviteCodeResponse:
        base = settings.FRONTEND_URL.rstrip("/")
        code = row["code"]
        return InviteCodeResponse(
            id=UUID(str(row["id"])),
            code=code,
            label=row.get("label"),
            max_uses=int(row.get("max_uses") or 0),
            use_count=int(row.get("use_count") or 0),
            expires_at=row.get("expires_at"),
            is_active=bool(row.get("is_active", True)),
            created_at=row["created_at"],
            invite_url=f"{base}/?invite={code}",
        )

    async def _fetch_code_row(self, code: str) -> Optional[dict]:
        client = get_supabase()

        def _q():
            return (
                client.table(INVITE_TABLE)
                .select("*")
                .eq("code", code)
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_q)
        return result.data

    async def _get_member(self, user_id: str) -> Optional[dict]:
        client = get_supabase()

        def _q():
            return (
                client.table(MEMBERS_TABLE)
                .select("*")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )

        result = await run_supabase(_q)
        return result.data

    async def _insert_member(
        self,
        *,
        user_id: str,
        email: str,
        display_name: Optional[str],
        invite_code_id: str,
        invite_code: str,
    ) -> None:
        client = get_supabase()
        payload = {
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "invite_code_id": invite_code_id,
            "invite_code": invite_code,
        }

        def _ins():
            return client.table(MEMBERS_TABLE).insert(payload).execute()

        await run_supabase(_ins)

    async def _increment_use_count(self, invite_id: str, current: int) -> None:
        client = get_supabase()

        def _upd():
            return (
                client.table(INVITE_TABLE)
                .update({"use_count": current + 1})
                .eq("id", invite_id)
                .execute()
            )

        await run_supabase(_upd)

    def _code_usable_error(self, row: dict) -> Optional[str]:
        if not row.get("is_active", True):
            return "Код деактивовано"
        max_uses = int(row.get("max_uses") or 0)
        use_count = int(row.get("use_count") or 0)
        if use_count >= max_uses:
            return "Код вичерпано"
        exp = row.get("expires_at")
        if exp:
            try:
                expires = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                if expires < datetime.now(timezone.utc):
                    return "Термін дії коду закінчився"
            except ValueError:
                pass
        return None


def get_invite_service() -> InviteService:
    return InviteService()
