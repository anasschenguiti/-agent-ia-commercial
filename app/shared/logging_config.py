"""
Configuration structlog et OpenTelemetry pour la journalisation JSON et l'observabilité.
"""
import sys
import logging
from app.shared.config import settings


def configure_logging():
    """Initialise la journalisation structurée structlog (JSON en prod, lisible en dev) avec fallback stdlib."""
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    try:
        import structlog

        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
        ]

        if settings.APP_ENV == "production":
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))

        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(log_level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    except ImportError:
        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stdout,
            level=log_level,
        )


def setup_opentelemetry(app):
    """Active l'instrumentation OpenTelemetry pour FastAPI si l'endpoint OTLP est configuré."""
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        provider = TracerProvider()
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        FastAPIInstrumentor.instrument_app(app)
        logging.info("OpenTelemetry instrumentation activée avec succès.")
    except Exception as e:
        logging.warning(f"OpenTelemetry non initialisé ({e}). Tracing ignoré.")
