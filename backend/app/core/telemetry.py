"""OpenTelemetry setup for DocMind OS."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def setup_telemetry(app=None) -> None:
    """Initialize OpenTelemetry tracing. No-op if OTEL_ENABLED=False."""
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    resource = Resource.create(
        {
            SERVICE_NAME: settings.APP_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.OTEL_EXPORTER_ENDPOINT:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_ENDPOINT,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info("OTel exporter: %s", settings.OTEL_EXPORTER_ENDPOINT)
        except Exception as exc:
            logger.warning("OTel exporter setup failed: %s", exc)

    trace.set_tracer_provider(provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI auto-instrumented with OpenTelemetry")


def get_tracer(name: str):
    """Get a tracer for manual instrumentation."""
    return trace.get_tracer(name)
