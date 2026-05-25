"""Tests for startup security validation."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.startup_validation import StartupSecurityError, run_startup_security_checks


def _make_settings(**kwargs):
    settings = MagicMock()
    settings.ENVIRONMENT = kwargs.get("ENVIRONMENT", "development")
    settings.AUTH_DISABLED = kwargs.get("AUTH_DISABLED", False)
    settings.auth_disabled = kwargs.get("auth_disabled", False)
    settings.SECRET_KEY = kwargs.get("SECRET_KEY", "super-secret-key-that-is-long-enough-32c")
    settings.DEBUG = kwargs.get("DEBUG", False)
    settings.API_DEBUG = kwargs.get("API_DEBUG", False)
    settings.LOG_LEVEL = kwargs.get("LOG_LEVEL", "INFO")
    settings.BACKEND_CORS_ORIGINS = kwargs.get("BACKEND_CORS_ORIGINS", ["http://localhost:3000"])
    settings.cors_origins_list = kwargs.get("cors_origins_list", ["http://localhost:3000"])
    settings.SUPABASE_SERVICE_ROLE_KEY = kwargs.get("SUPABASE_SERVICE_ROLE_KEY", None)
    return settings


def test_dev_with_auth_disabled_is_ok():
    settings = _make_settings(
        ENVIRONMENT="development",
        AUTH_DISABLED=True,
        auth_disabled=True,
    )
    with patch.dict("os.environ", {"AUTH_DISABLED": "true", "ENVIRONMENT": "development"}):
        run_startup_security_checks(settings)


def test_production_with_auth_disabled_raises():
    settings = _make_settings(
        ENVIRONMENT="production",
        AUTH_DISABLED=True,
        auth_disabled=True,
    )
    with patch.dict("os.environ", {"AUTH_DISABLED": "true", "ENVIRONMENT": "production"}):
        with pytest.raises(StartupSecurityError):
            run_startup_security_checks(settings)


def test_staging_with_auth_disabled_raises():
    settings = _make_settings(
        ENVIRONMENT="staging",
        AUTH_DISABLED=True,
        auth_disabled=True,
    )
    with patch.dict("os.environ", {"AUTH_DISABLED": "true", "ENVIRONMENT": "staging"}):
        with pytest.raises(StartupSecurityError):
            run_startup_security_checks(settings)


def test_production_normal_config_passes():
    settings = _make_settings(ENVIRONMENT="production", auth_disabled=False)
    with patch.dict("os.environ", {"AUTH_DISABLED": "false", "ENVIRONMENT": "production"}):
        run_startup_security_checks(settings)


def test_weak_secret_in_production_raises():
    settings = _make_settings(ENVIRONMENT="production", SECRET_KEY="changeme")
    with patch.dict("os.environ", {"AUTH_DISABLED": "false"}):
        with pytest.raises(StartupSecurityError):
            run_startup_security_checks(settings)


def test_debug_true_in_production_raises():
    settings = _make_settings(ENVIRONMENT="production", DEBUG=True)
    with patch.dict("os.environ", {"AUTH_DISABLED": "false"}):
        with pytest.raises(StartupSecurityError):
            run_startup_security_checks(settings)


def test_api_debug_true_in_production_raises():
    settings = _make_settings(ENVIRONMENT="production", API_DEBUG=True)
    with patch.dict("os.environ", {"AUTH_DISABLED": "false"}):
        with pytest.raises(StartupSecurityError):
            run_startup_security_checks(settings)
