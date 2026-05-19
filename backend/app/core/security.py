from typing import Annotated, Any, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.db.supabase import get_supabase, run_supabase

security_scheme = HTTPBearer(auto_error=False)

# Well-known dev user UUID (valid uuid format)
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def _dev_user() -> dict[str, Any]:
    return {
        "id": DEV_USER_ID,
        "email": "dev@docmind.local",
        "role": "authenticated",
        "org_id": None,
        "app_metadata": {},
        "user_metadata": {},
    }


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(security_scheme)
    ],
) -> dict[str, Any]:
    """
    Validate Supabase JWT and return the authenticated user context.

  In development, set AUTH_DISABLED=true to use a fixed dev user (tests/local only).
    """
    if settings.auth_disabled:
        return _dev_user()

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.supabase_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    token = credentials.credentials
    try:
        client = get_supabase()

        def _get_user():
            return client.auth.get_user(token)

        response = await run_supabase(_get_user)
        if response.user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        user = response.user
        app_meta = user.app_metadata or {}
        user_meta = user.user_metadata or {}

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "org_id": app_meta.get("org_id") or user_meta.get("org_id"),
            "app_metadata": app_meta,
            "user_metadata": user_meta,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def get_current_org(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
    x_org_id: Annotated[Optional[str], Header(alias="X-Org-ID")] = None,
) -> Optional[str]:
    """
    Resolve organization scope for the request.

    Priority: X-Org-ID header > JWT org_id claim > None (personal workspace).
    """
    if x_org_id:
        return x_org_id
    org_id = current_user.get("org_id")
    return str(org_id) if org_id else None


async def get_admin_user(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """Pilot admin — email must be listed in PILOT_ADMIN_EMAILS."""
    email = (current_user.get("email") or "").lower()
    if settings.auth_disabled and email == "dev@docmind.local":
        return current_user
    if email not in settings.pilot_admin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def get_current_user_optional(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(security_scheme)
    ],
) -> Optional[dict[str, Any]]:
    """Optional auth — returns None instead of 401."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
