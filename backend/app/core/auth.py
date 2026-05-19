"""Auth dependencies — re-exported from security for API endpoints."""

from app.core.security import get_current_user

__all__ = ["get_current_user"]
