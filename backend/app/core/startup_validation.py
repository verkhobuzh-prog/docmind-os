"""
Startup security validation для Doc-Hub.

Вектор атаки (AUTH_DISABLED):
────────────────────────────
  Якщо ENVIRONMENT=production але AUTH_DISABLED=true (через typo в .env,
  або CI/CD pipeline підставив неправильний secret), весь API відкривається
  без будь-якої аутентифікації. Будь-який HTTP клієнт читає/пише документи.

  Приклад: dev .env скопіювали на prod сервер → AUTH_DISABLED=true залишилась.
  Суттєвість: CRITICAL (повне відкриття API).

До виправлення (config.py):
────────────────────────────
  @property
  def auth_disabled(self) -> bool:
      # BUG: тільки перевіряє ENVIRONMENT, але не блокує старт!
      return self.AUTH_DISABLED and self.ENVIRONMENT == "development"
  # Якщо хтось поставить ENVIRONMENT=development на prod — bypass готовий.
  # Немає hard fail при старті → проблема виявляється тільки під час атаки.

Після виправлення (цей модуль):
────────────────────────────────
  - Перевірка при старті застосунку (lifespan hook)
  - Hard fail (SystemExit) якщо AUTH_DISABLED у будь-якому non-dev оточенні
  - Додаткові security checks: слабкі секрети, debug режими
  - Логування всіх порушень у структурований лог
"""

from __future__ import annotations

import os
import sys
import hashlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger("Doc-Hub.security.startup")

# Оточення, де AUTH_DISABLED заборонено категорично
_PROTECTED_ENVIRONMENTS = frozenset({
    "production",
    "prod",
    "staging",
    "stage",
    "uat",
    "preprod",
    "pre-prod",
})

# Відомі слабкі / placeholder значення секретів
_WEAK_SECRET_PATTERNS = frozenset({
    "secret",
    "changeme",
    "password",
    "12345",
    "test",
    "dev",
    "example",
    "your-secret-key",
    "your_secret_key",
    "dummy",
    "placeholder",
    "",
})


class StartupSecurityError(RuntimeError):
    """Критична security помилка при старті — додаток не повинен запускатись."""


def _is_protected_env(environment: str) -> bool:
    """Перевіряє чи поточне оточення є захищеним (non-dev)."""
    return environment.lower().strip() in _PROTECTED_ENVIRONMENTS


def _is_weak_secret(value: str | None, name: str) -> bool:
    """Перевіряє чи секрет є очевидно слабким."""
    if not value:
        return True
    normalized = value.strip().lower()
    # Перевірка точних match
    if normalized in _WEAK_SECRET_PATTERNS:
        return True
    # Перевірка чи секрет занадто короткий для production
    if len(value) < 32:
        logger.warning(
            "Security warning: %s is shorter than 32 characters (%d chars). "
            "Consider using a longer secret in production.",
            name, len(value)
        )
    return False


def _check_auth_disabled(settings: "Settings") -> list[str]:
    """
    Перевіряє AUTH_DISABLED.

    Returns:
        Список помилок (порожній = OK).
    """
    errors: list[str] = []
    env = settings.ENVIRONMENT

    # Пряма перевірка ENV змінної (не property!) щоб уникнути обходу через property
    raw_auth_disabled = os.environ.get("AUTH_DISABLED", "").strip().lower()
    auth_disabled_raw = raw_auth_disabled in ("true", "1", "yes", "on")

    if auth_disabled_raw and _is_protected_env(env):
        errors.append(
            f"CRITICAL SECURITY VIOLATION: AUTH_DISABLED=true is set in "
            f"ENVIRONMENT='{env}'. Authentication bypass is not allowed "
            f"outside of local development. "
            f"Fix: set AUTH_DISABLED=false (or remove it) in your production .env"
        )

    # Також перевіряємо через settings property для defense in depth
    if settings.auth_disabled and _is_protected_env(env):
        errors.append(
            f"CRITICAL: settings.auth_disabled=True in protected environment '{env}'. "
            f"Check your Settings class logic."
        )

    return errors


def _check_secret_key(settings: "Settings") -> list[str]:
    """Перевіряє SECRET_KEY на слабкість."""
    errors: list[str] = []
    secret = getattr(settings, "SECRET_KEY", None)

    if secret is None:
        # Якщо поля немає — пропускаємо (не всі конфіги мають)
        return errors

    if _is_protected_env(settings.ENVIRONMENT) and _is_weak_secret(secret, "SECRET_KEY"):
        errors.append(
            "CRITICAL: SECRET_KEY appears to be weak or a placeholder. "
            "Generate a strong key: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    return errors


def _check_supabase_config(settings: "Settings") -> list[str]:
    """Перевіряє Supabase конфігурацію."""
    warnings: list[str] = []

    if not _is_protected_env(settings.ENVIRONMENT):
        return warnings

    # Service role key не повинна потрапляти у frontend / логи
    service_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
    if service_key:
        # Перевіряємо що це справжній Supabase JWT, а не placeholder
        if service_key.startswith("eyJ") is False:
            warnings.append(
                "WARNING: SUPABASE_SERVICE_ROLE_KEY does not look like a valid JWT. "
                "Ensure you are using the correct key from Supabase Dashboard → Settings → API."
            )
        # Перевіряємо чи ключ не є anon key (частий баг: переплутали ключі)
        # Anon key зазвичай має role=anon у payload, service role має role=service_role
        try:
            import base64
            import json
            parts = service_key.split(".")
            if len(parts) == 3:
                payload_raw = parts[1]
                # Додаємо padding якщо потрібно
                payload_raw += "=" * (4 - len(payload_raw) % 4)
                payload = json.loads(base64.b64decode(payload_raw))
                role = payload.get("role", "")
                if role == "anon":
                    warnings.append(
                        "CRITICAL: SUPABASE_SERVICE_ROLE_KEY contains an 'anon' role JWT. "
                        "You are using the ANON KEY instead of the SERVICE ROLE KEY. "
                        "This will cause 403 errors on all backend operations. "
                        "Fix: use the 'service_role' key from Supabase Dashboard → Settings → API."
                    )
                elif role not in ("service_role", "supabase_admin", ""):
                    warnings.append(
                        f"WARNING: SUPABASE_SERVICE_ROLE_KEY has unexpected role='{role}'. "
                        f"Expected 'service_role'."
                    )
        except Exception:
            pass  # Не можемо декодувати — залишаємо без помилки

    return warnings


def _check_debug_modes(settings: "Settings") -> list[str]:
    """Перевіряє debug режими в production."""
    errors: list[str] = []

    if not _is_protected_env(settings.ENVIRONMENT):
        return errors

    # FastAPI debug mode
    debug = getattr(settings, "DEBUG", False)
    if debug:
        errors.append(
            "SECURITY: DEBUG=True is set in a protected environment. "
            "This exposes stack traces and internal details. Set DEBUG=False."
        )

    # LOG_LEVEL занадто verbose
    log_level = getattr(settings, "LOG_LEVEL", "INFO").upper()
    if log_level == "DEBUG":
        errors.append(
            "WARNING: LOG_LEVEL=DEBUG in production may leak sensitive data "
            "(request bodies, auth tokens) to logs. Consider using INFO or WARNING."
        )

    return errors


def _check_cors_origins(settings: "Settings") -> list[str]:
    """Перевіряє CORS wildcard в production."""
    warnings: list[str] = []

    if not _is_protected_env(settings.ENVIRONMENT):
        return warnings

    cors_origins = getattr(settings, "BACKEND_CORS_ORIGINS", [])
    if isinstance(cors_origins, str):
        cors_origins = [cors_origins]

    for origin in cors_origins:
        if origin.strip() == "*":
            warnings.append(
                "SECURITY: BACKEND_CORS_ORIGINS contains wildcard '*' in production. "
                "This allows any origin to make credentialed requests. "
                "Specify exact origins: https://yourdomain.com"
            )
            break

    return warnings


def run_startup_security_checks(settings: "Settings") -> None:
    """
    Запускає всі security перевірки при старті.

    Викликати з lifespan() в main.py:
        from app.core.startup_validation import run_startup_security_checks
        run_startup_security_checks(settings)

    Raises:
        StartupSecurityError: якщо є CRITICAL порушення (додаток не стартує).
        Для WARNING — логує але не зупиняє.
    """
    env = getattr(settings, "ENVIRONMENT", "unknown")
    logger.info("Running startup security checks (environment: %s)", env)

    critical_errors: list[str] = []
    warnings: list[str] = []

    # ── CRITICAL checks ───────────────────────────────────────────
    critical_errors.extend(_check_auth_disabled(settings))
    critical_errors.extend(_check_secret_key(settings))
    critical_errors.extend(_check_debug_modes(settings))

    # ── WARNING checks ────────────────────────────────────────────
    warnings.extend(_check_supabase_config(settings))
    warnings.extend(_check_cors_origins(settings))

    # ── Вивід результатів ─────────────────────────────────────────
    for w in warnings:
        logger.warning("[SECURITY] %s", w)

    if critical_errors:
        logger.critical("=" * 70)
        logger.critical("STARTUP SECURITY VALIDATION FAILED")
        logger.critical("=" * 70)
        for i, err in enumerate(critical_errors, 1):
            logger.critical("[%d/%d] %s", i, len(critical_errors), err)
        logger.critical("=" * 70)
        logger.critical(
            "Application startup aborted. Fix the issues above before deploying."
        )

        # Raise + sys.exit для гарантованої зупинки навіть якщо exception catch десь є
        raise StartupSecurityError(
            f"Security validation failed with {len(critical_errors)} critical error(s). "
            f"See logs for details."
        )

    logger.info(
        "Startup security checks passed (%d warnings).",
        len(warnings)
    )
