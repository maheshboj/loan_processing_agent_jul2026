import os
from opentelemetry import trace

# We initialize this globally as None
_tracer_provider = None

def init_arize_tracing():
    global _tracer_provider
    if _tracer_provider is not None:
        return _tracer_provider

    # Read config from environment variables (checking both standard and lower-case variants)
    api_key = os.environ.get("ARIZE_API_KEY")
    space_id = os.environ.get("ARIZE_SPACE_ID") or os.environ.get("space_id")
    project_name = os.environ.get("ARIZE_PROJECT_NAME") or os.environ.get("project_name") or "LOANAGENTS"

    if not api_key or not space_id:
        print("[Arize] Tracing not initialized: ARIZE_API_KEY and space_id / ARIZE_SPACE_ID must be configured.")
        return None

    try:
        from arize.otel import register
        from openinference.instrumentation.crewai import CrewAIInstrumentor
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from openinference.instrumentation.litellm import LiteLLMInstrumentor

        # Register the provider
        _tracer_provider = register(
            space_id=space_id,
            api_key=api_key,
            project_name=project_name,
        )

        # Attach instrumentors
        CrewAIInstrumentor().instrument(tracer_provider=_tracer_provider)
        OpenAIInstrumentor().instrument(tracer_provider=_tracer_provider)
        LiteLLMInstrumentor().instrument(tracer_provider=_tracer_provider)

        print(f"[Arize] Tracing initialized successfully for project: {project_name}")
        return _tracer_provider
    except Exception as e:
        print(f"[Arize] Failed to initialize tracing: {e}")
        return None

def flush_arize_spans():
    global _tracer_provider
    if _tracer_provider:
        try:
            print("[Arize] Flushing OTel spans...")
            _tracer_provider.force_flush()
            print("[Arize] Spans flushed successfully.")
        except Exception as e:
            print(f"[Arize] Error flushing spans: {e}")

def shutdown_arize_tracing():
    global _tracer_provider
    if _tracer_provider:
        try:
            print("[Arize] Shutting down tracing...")
            _tracer_provider.force_flush()
            _tracer_provider.shutdown()
            _tracer_provider = None
            print("[Arize] Tracing shut down successfully.")
        except Exception as e:
            print(f"[Arize] Error shutting down tracing: {e}")
