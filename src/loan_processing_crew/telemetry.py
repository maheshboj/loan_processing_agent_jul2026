import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.trace import Status, StatusCode

# Import crewai events
from crewai.events.event_bus import crewai_event_bus
from crewai.events.types.crew_events import (
    CrewKickoffStartedEvent,
    CrewKickoffCompletedEvent,
    CrewKickoffFailedEvent,
)
from crewai.events.types.task_events import (
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
)
from crewai.events.types.tool_usage_events import (
    ToolUsageStartedEvent,
    ToolUsageFinishedEvent,
    ToolUsageErrorEvent,
)
from crewai.events.types.llm_events import (
    LLMCallStartedEvent,
    LLMCallCompletedEvent,
    LLMCallFailedEvent,
)

# Thread-local storage to track the active application_id
_thread_local = threading.local()

# Maps event_id (str) -> Span
_spans_map: Dict[str, trace.Span] = {}
# Maps event_id (str) -> application_id (str)
_event_app_map: Dict[str, str] = {}
# Active crew span (single-run process environment)
_active_crew_span: Optional[trace.Span] = None
# Active application ID (single-run process environment)
_active_application_id: str = "unknown"
# Maps event_id (str) -> task_id (str)
_event_task_id_map: Dict[str, str] = {}

_telemetry_initialized = False
_db_path = Path("output") / "telemetry.db"


class SQLiteSpanExporter(SpanExporter):
    """
    A custom OpenTelemetry SpanExporter that persists spans and metadata to SQLite.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(self.db_path.parent, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spans (
                span_id TEXT PRIMARY KEY,
                trace_id TEXT,
                parent_span_id TEXT,
                name TEXT,
                application_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_ms REAL,
                type TEXT,
                status TEXT,
                error_message TEXT,
                attributes TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id TEXT PRIMARY KEY,
                application_id TEXT,
                timestamp TIMESTAMP,
                check_name TEXT,
                status TEXT,
                detail TEXT
            )
        """)
        conn.commit()
        conn.close()

    def export(self, spans: List[ReadableSpan]) -> SpanExportResult:
        print(f"[Telemetry Debug] SQLiteSpanExporter.export called with {len(spans)} spans")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            for span in spans:
                attrs = dict(span.attributes)
                app_id = attrs.get("loan.application_id")
                span_type = attrs.get("span.type", "unknown")
                print(f"[Telemetry Debug] Exporting span: name={span.name}, type={span_type}, app_id={app_id}")

                # Token usage & costs
                prompt_tokens = attrs.get("gen_ai.usage.prompt_tokens", 0)
                completion_tokens = attrs.get("gen_ai.usage.completion_tokens", 0)
                total_tokens = attrs.get("gen_ai.usage.total_tokens", 0)
                cost = attrs.get("gen_ai.usage.cost", 0.0)

                status = span.status.status_code.name
                error_message = span.status.description

                start_time_iso = (
                    datetime.fromtimestamp(span.start_time / 1e9).isoformat()
                    if span.start_time
                    else None
                )
                end_time_iso = (
                    datetime.fromtimestamp(span.end_time / 1e9).isoformat()
                    if span.end_time
                    else None
                )
                duration_ms = (
                    (span.end_time - span.start_time) / 1e6
                    if (span.start_time and span.end_time)
                    else 0.0
                )

                # Ensure span_id and trace_id are strings
                span_id_hex = format(span.context.span_id, "016x")
                trace_id_hex = format(span.context.trace_id, "032x")
                parent_span_id_hex = (
                    format(span.parent.span_id, "016x")
                    if span.parent
                    else None
                )

                cursor.execute("""
                    INSERT OR REPLACE INTO spans (
                        span_id, trace_id, parent_span_id, name, application_id,
                        start_time, end_time, duration_ms, type, status,
                        error_message, attributes, prompt_tokens, completion_tokens,
                        total_tokens, cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    span_id_hex,
                    trace_id_hex,
                    parent_span_id_hex,
                    span.name,
                    app_id,
                    start_time_iso,
                    end_time_iso,
                    duration_ms,
                    span_type,
                    status,
                    error_message,
                    json.dumps(attrs),
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    cost
                ))
            conn.commit()
            conn.close()
            return SpanExportResult.SUCCESS
        except Exception as e:
            print(f"Error exporting spans: {e}")
            return SpanExportResult.FAILED_RETRY

    def shutdown(self):
        pass


def record_audit_log(application_id: str, check_name: str, status: str, detail: str):
    """
    Inserts a compliance audit log into SQLite.
    """
    try:
        conn = sqlite3.connect(_db_path)
        cursor = conn.cursor()
        log_id = f"log_{datetime.now().timestamp()}_{check_name.replace(' ', '_')}"
        cursor.execute("""
            INSERT INTO audit_logs (log_id, application_id, timestamp, check_name, status, detail)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (log_id, application_id, datetime.now().isoformat(), check_name, status, detail))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error recording audit log: {e}")


def init_telemetry():
    """
    Initializes OpenTelemetry TracerProvider, SQLiteSpanExporter, and registers crewai event listeners.
    """
    global _telemetry_initialized
    if _telemetry_initialized:
        return

    # Setup OpenTelemetry tracer provider
    provider = TracerProvider()
    exporter = SQLiteSpanExporter(_db_path)
    # SimpleSpanProcessor exports immediately (good for single run scripts)
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)
    try:
        trace.set_tracer_provider(provider)
    except RuntimeError:
        pass

    tracer = provider.get_tracer("loan_processing_crew")

    # Register Event Handlers
    @crewai_event_bus.on(CrewKickoffStartedEvent)
    def on_crew_kickoff_started(source, event: CrewKickoffStartedEvent):
        global _active_crew_span, _active_application_id
        inputs = event.inputs or {}
        app_id = inputs.get("application_id", "unknown")
        _active_application_id = app_id
        _thread_local.application_id = app_id
        _event_app_map[event.event_id] = app_id
        print(f"[Telemetry Debug] CrewKickoffStartedEvent: app={app_id}, event_id={event.event_id}, parent={event.parent_event_id}")

        span = tracer.start_span("crew_kickoff")
        span.set_attribute("loan.application_id", app_id)
        span.set_attribute("crew.name", event.crew_name or "Loan Processing Crew")
        span.set_attribute("span.type", "crew")
        _active_crew_span = span

    @crewai_event_bus.on(CrewKickoffCompletedEvent)
    def on_crew_kickoff_completed(source, event: CrewKickoffCompletedEvent):
        global _active_crew_span
        print(f"[Telemetry Debug] CrewKickoffCompletedEvent: event_id={event.event_id}, triggered_by={event.triggered_by_event_id}, parent={event.parent_event_id}")
        span = _active_crew_span
        if span:
            span.set_status(Status(StatusCode.OK))
            # Mark workflow verification status based on outputs
            output = getattr(event, "output", None)
            if output:
                output_raw = getattr(output, "raw", "")
                if "APPROVED" in output_raw.upper() or "APPROVE" in output_raw.upper():
                    span.set_attribute("loan.verification_status", "APPROVED")
                elif "CONDITIONALLY" in output_raw.upper():
                    span.set_attribute("loan.verification_status", "CONDITIONALLY APPROVED")
                elif "DECLINED" in output_raw.upper() or "DECLINE" in output_raw.upper():
                    span.set_attribute("loan.verification_status", "DECLINED")
                else:
                    span.set_attribute("loan.verification_status", "COMPLETED")
            span.end()
            _active_crew_span = None

    @crewai_event_bus.on(CrewKickoffFailedEvent)
    def on_crew_kickoff_failed(source, event: CrewKickoffFailedEvent):
        global _active_crew_span
        print(f"[Telemetry Debug] CrewKickoffFailedEvent: event_id={event.event_id}, triggered_by={event.triggered_by_event_id}, parent={event.parent_event_id}")
        span = _active_crew_span
        if span:
            span.set_status(Status(StatusCode.ERROR, str(event.error)))
            span.set_attribute("loan.verification_status", "FAILED")
            span.end()
            _active_crew_span = None

    @crewai_event_bus.on(TaskStartedEvent)
    def on_task_started(source, event: TaskStartedEvent):
        app_id = _active_application_id
        _event_app_map[event.event_id] = app_id
        print(f"[Telemetry Debug] TaskStartedEvent: event_id={event.event_id}")
        
        parent_span = _active_crew_span
        ctx = trace.set_span_in_context(parent_span) if parent_span else None
        
        task_id = event.task_id or (event.task.id if hasattr(event, "task") and event.task else "unknown")
        task_name = event.task_name or (getattr(event.task, "description", "").split("\n")[0][:40] if hasattr(event, "task") and event.task else "task")
        
        # Track mapping from event ID to task ID
        _event_task_id_map[event.event_id] = str(task_id)
        
        span = tracer.start_span(task_name or "task", context=ctx)
        span.set_attribute("loan.application_id", app_id)
        span.set_attribute("task.id", str(task_id))
        span.set_attribute("task.name", str(task_name))
        span.set_attribute("agent.role", event.agent_role or "unknown")
        span.set_attribute("span.type", "task")
        
        _spans_map[f"task_{task_id}"] = span

    @crewai_event_bus.on(TaskCompletedEvent)
    def on_task_completed(source, event: TaskCompletedEvent):
        task_id = event.task_id or (event.task.id if hasattr(event, "task") and event.task else "unknown")
        print(f"[Telemetry Debug] TaskCompletedEvent: task_id={task_id}")
        span = _spans_map.get(f"task_{task_id}")
        if span:
            span.set_status(Status(StatusCode.OK))
            output = getattr(event, "output", "")
            if output:
                span.set_attribute("task.output_preview", str(output)[:1000])
            span.end()
            _spans_map.pop(f"task_{task_id}", None)

    @crewai_event_bus.on(TaskFailedEvent)
    def on_task_failed(source, event: TaskFailedEvent):
        task_id = event.task_id or (event.task.id if hasattr(event, "task") and event.task else "unknown")
        print(f"[Telemetry Debug] TaskFailedEvent: task_id={task_id}")
        span = _spans_map.get(f"task_{task_id}")
        if span:
            span.set_status(Status(StatusCode.ERROR, str(event.error)))
            span.end()
            _spans_map.pop(f"task_{task_id}", None)

    @crewai_event_bus.on(ToolUsageStartedEvent)
    def on_tool_started(source, event: ToolUsageStartedEvent):
        app_id = _active_application_id
        _event_app_map[event.event_id] = app_id
        
        task_id = _event_task_id_map.get(event.parent_event_id)
        parent_span = _spans_map.get(f"task_{task_id}") if task_id else None
        ctx = trace.set_span_in_context(parent_span) if parent_span else None
        
        span = tracer.start_span(f"tool:{event.tool_name}", context=ctx)
        span.set_attribute("loan.application_id", app_id)
        span.set_attribute("tool.name", event.tool_name)
        span.set_attribute("tool.class", event.tool_class or "unknown")
        span.set_attribute("tool.args", json.dumps(event.tool_args or {}))
        span.set_attribute("span.type", "tool")
        
        _spans_map[f"tool_{event.parent_event_id}_{event.tool_name}"] = span

    @crewai_event_bus.on(ToolUsageFinishedEvent)
    def on_tool_finished(source, event: ToolUsageFinishedEvent):
        span = _spans_map.get(f"tool_{event.parent_event_id}_{event.tool_name}")
        if span:
            span.set_status(Status(StatusCode.OK))
            output_str = str(event.output or "")
            span.set_attribute("tool.output_preview", output_str[:1000])
            
            # Parse compliance logs if Regulatory Compliance Checker tool is run
            app_id = _active_application_id
            if event.tool_name in ("Regulatory Compliance Checker", "regulatory_compliance_checker") and output_str:
                try:
                    data = json.loads(output_str)
                    checks = data.get("checks", [])
                    for check in checks:
                        record_audit_log(
                            application_id=app_id,
                            check_name=check.get("check", "Unknown Check"),
                            status=check.get("status", "UNKNOWN"),
                            detail=check.get("detail", "")
                        )
                except Exception as e:
                    print(f"Failed parsing compliance checker tool logs: {e}")
                    
            span.end()
            _spans_map.pop(f"tool_{event.parent_event_id}_{event.tool_name}", None)

    @crewai_event_bus.on(ToolUsageErrorEvent)
    def on_tool_error(source, event: ToolUsageErrorEvent):
        span = _spans_map.get(f"tool_{event.parent_event_id}_{event.tool_name}")
        if span:
            span.set_status(Status(StatusCode.ERROR, str(event.error)))
            span.end()
            _spans_map.pop(f"tool_{event.parent_event_id}_{event.tool_name}", None)

    @crewai_event_bus.on(LLMCallStartedEvent)
    def on_llm_started(source, event: LLMCallStartedEvent):
        app_id = _active_application_id
        _event_app_map[event.event_id] = app_id
        
        task_id = _event_task_id_map.get(event.parent_event_id)
        parent_span = _spans_map.get(f"task_{task_id}") if task_id else None
        ctx = trace.set_span_in_context(parent_span) if parent_span else None
        
        span = tracer.start_span("llm_completion", context=ctx)
        span.set_attribute("loan.application_id", app_id)
        span.set_attribute("gen_ai.system", "openai")
        span.set_attribute("gen_ai.request.model", event.model or "gpt-4o")
        span.set_attribute("span.type", "llm")
        
        _spans_map[f"llm_{event.parent_event_id}"] = span

    @crewai_event_bus.on(LLMCallCompletedEvent)
    def on_llm_completed(source, event: LLMCallCompletedEvent):
        span = _spans_map.get(f"llm_{event.parent_event_id}")
        if span:
            span.set_status(Status(StatusCode.OK))
            span.set_attribute("gen_ai.response.model", event.model or "gpt-4o")

            # Extract token usage details
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            
            response = getattr(event, "response", None)
            if response:
                # Handle standard OpenAI/LiteLLM ChatCompletion response format
                usage = getattr(response, "usage", None)
                if usage:
                    prompt_tokens = (
                        getattr(usage, "prompt_tokens", 0)
                        or getattr(usage, "input_tokens", 0)
                        or 0
                    )
                    completion_tokens = (
                        getattr(usage, "completion_tokens", 0)
                        or getattr(usage, "output_tokens", 0)
                        or 0
                    )
                    total_tokens = getattr(usage, "total_tokens", 0) or 0
                elif isinstance(response, dict):
                    usage = response.get("usage", {})
                    if isinstance(usage, dict):
                        prompt_tokens = (
                            usage.get("prompt_tokens", 0)
                            or usage.get("input_tokens", 0)
                            or 0
                        )
                        completion_tokens = (
                            usage.get("completion_tokens", 0)
                            or usage.get("output_tokens", 0)
                            or 0
                        )
                        total_tokens = usage.get("total_tokens", 0) or 0

            # Dynamic token cost calculation
            model_name = (event.model or "").lower()
            input_rate = 0.0000025
            output_rate = 0.000010
            
            if "gpt-4" in model_name:
                if "gpt-4o" in model_name:
                    input_rate = 0.0000025
                    output_rate = 0.000010
                else:
                    input_rate = 0.000030
                    output_rate = 0.000060
            elif "claude-3" in model_name:
                input_rate = 0.000003
                output_rate = 0.000015

            cost = (prompt_tokens * input_rate) + (completion_tokens * output_rate)

            span.set_attribute("gen_ai.usage.prompt_tokens", prompt_tokens)
            span.set_attribute("gen_ai.usage.completion_tokens", completion_tokens)
            span.set_attribute("gen_ai.usage.total_tokens", total_tokens)
            span.set_attribute("gen_ai.usage.cost", cost)
            
            span.end()
            _spans_map.pop(f"llm_{event.parent_event_id}", None)

    @crewai_event_bus.on(LLMCallFailedEvent)
    def on_llm_failed(source, event: LLMCallFailedEvent):
        span = _spans_map.get(f"llm_{event.parent_event_id}")
        if span:
            span.set_status(Status(StatusCode.ERROR, str(event.error)))
            span.end()
            _spans_map.pop(f"llm_{event.parent_event_id}", None)

    _telemetry_initialized = True
