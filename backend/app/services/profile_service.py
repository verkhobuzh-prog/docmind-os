from __future__ import annotations

from fastapi import HTTPException

from app.db.supabase import get_supabase, run_supabase
from app.schemas.profile import ProfileCreate, ProfilePreferences, ProfileRead, ProfileUpdate


class ProfileService:
    def __init__(self) -> None:
        self.sb = get_supabase()

    # ---------- helpers ----------
    def _row_to_schema(self, row: dict) -> ProfileRead:
        prefs_raw = row.get("preferences") or {}
        row["preferences"] = ProfilePreferences(**prefs_raw)
        return ProfileRead(**row)

    # ---------- CRUD ----------
    async def list_profiles(self, user_id: str) -> list[ProfileRead]:
        result = await run_supabase(
            lambda: self.sb.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return [self._row_to_schema(r) for r in (result.data or [])]

    async def get_active_profile(self, user_id: str) -> ProfileRead | None:
        result = await run_supabase(
            lambda: self.sb.table("user_profiles")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        if not result.data:
            return None
        return self._row_to_schema(result.data)

    async def create_profile(self, user_id: str, data: ProfileCreate) -> ProfileRead:
        existing = await self.list_profiles(user_id)

        payload = {
            "user_id": user_id,
            "name": data.name,
            "complexity_level": data.complexity_level,
            "domain": data.domain,
            "preferences": data.preferences.model_dump(),
            "is_active": len(existing) == 0,
        }
        result = await run_supabase(
            lambda: self.sb.table("user_profiles").insert(payload).execute()
        )
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create profile")
        return self._row_to_schema(result.data[0])

    async def update_profile(
        self, profile_id: str, user_id: str, data: ProfileUpdate
    ) -> ProfileRead:
        payload: dict = {}
        if data.name is not None:
            payload["name"] = data.name
        if data.complexity_level is not None:
            payload["complexity_level"] = data.complexity_level
        if data.domain is not None:
            payload["domain"] = data.domain
        if data.preferences is not None:
            payload["preferences"] = data.preferences.model_dump()

        if not payload:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = await run_supabase(
            lambda: self.sb.table("user_profiles")
            .update(payload)
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return self._row_to_schema(result.data[0])

    async def delete_profile(self, profile_id: str, user_id: str) -> None:
        result = await run_supabase(
            lambda: self.sb.table("user_profiles")
            .delete()
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")

    async def set_active(self, profile_id: str, user_id: str) -> ProfileRead:
        await run_supabase(
            lambda: self.sb.table("user_profiles")
            .update({"is_active": False})
            .eq("user_id", user_id)
            .execute()
        )
        result = await run_supabase(
            lambda: self.sb.table("user_profiles")
            .update({"is_active": True})
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        return self._row_to_schema(result.data[0])


def get_profile_service() -> ProfileService:
    return ProfileService()
