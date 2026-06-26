"""OpenTelemetry tracing configuration.

Sets up OTLP exporter for traces. In local development, traces are printed
to the console. In production, they can be sent to Cloud Trace / Jaeger / etc.
"""

from __future__ import annotations

from structlog import get_logger

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

logger = get_logger()


def configure_tracing(service_name: str = "rag-platform") -> None:
    """Configure OpenTelemetry tracing.

    Uses OTLP exporter if OTEL_EXPORTER_OTLP_ENDPOINT is set, otherwise
    falls back to console exporter.
    """
    import os

    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        logger.info("tracing_otlp_enabled", endpoint=otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()
        logger.info("tracing_console_enabled")

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: F401

        # This is called after the app is created in main.py
        logger.info("fastapi_instrumentation_available")
    except ImportError:
        logger.warning("opentelemetry_instrumentation_fastapi not installed")
