"""OpenTelemetry setup. Exports OTLP/HTTP to Grafana Cloud Tempo."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("Doc-Hub.telemetry")

_initialized = False


def init_telemetry(app) -> None:
    """Call once on app startup. Idempotent; no-op if not configured."""
    global _initialized
    if _initialized:
        return
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.info("OTEL endpoint not configured — telemetry disabled")
        return

    resource = Resource.create({
        "service.name": settings.APP_NAME.lower().replace(" ", "-"),
        "service.version": settings.APP_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)

    # Grafana Cloud auth: instanceID:token → base64
    headers = {}
    if settings.OTEL_GRAFANA_INSTANCE_ID and settings.OTEL_GRAFANA_API_TOKEN:
        creds = f"{settings.OTEL_GRAFANA_INSTANCE_ID}:{settings.OTEL_GRAFANA_API_TOKEN}"
        token = base64.b64encode(creds.encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    exporter = OTLPSpanExporter(
        endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/traces",
        headers=headers,
        timeout=10,
    )
    provider.add_span_processor(BatchSpanProcessor(
        exporter,
        max_queue_size=2048,
        max_export_batch_size=512,
        schedule_delay_millis=5000,
    ))
    trace.set_tracer_provider(provider)

    # Auto-instrument
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,docs,redoc,openapi.json",
    )
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()

    _initialized = True
    logger.info("OpenTelemetry initialized → %s", settings.OTEL_EXPORTER_OTLP_ENDPOINT)


def get_tracer(name: str = "Doc-Hub"):
    return trace.get_tracer(name)


@contextmanager
def traced_span(
    name: str,
    attributes: dict | None = None,
) -> Iterator[Span]:
    """Context manager that auto-records exceptions and sets ERROR status."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for k, v in attributes.items():
                span.set_attribute(k, v)
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
