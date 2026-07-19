"""
phoenix_eval.py — Phoenix Arize tracing + evaluation for Loan Processing Crew
Provides:
  - init_phoenix_tracing()  : Start Phoenix server + auto-instrument CrewAI
  - run_loan_evaluations()  : Run LLM-as-judge evals on collected traces
  - get_eval_summary()      : Return a DataFrame of eval scores for the dashboard
"""

import os
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Phoenix / OTel imports — wrapped so the rest of the app still loads even if
# Phoenix is not installed yet.
# ---------------------------------------------------------------------------
try:
    import phoenix as px
    from phoenix.otel import register as px_register
    from openinference.instrumentation.crewai import CrewAIInstrumentor
    PHOENIX_AVAILABLE = True
except ImportError:
    PHOENIX_AVAILABLE = False

# ---------------------------------------------------------------------------
# LiteLLM for LLM-as-judge evaluations
# ---------------------------------------------------------------------------
try:
    from litellm import completion as llm_completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Path for storing evaluation results alongside our existing telemetry DB
EVAL_DB_PATH = Path("output") / "phoenix_evals.db"
PHOENIX_URL = "http://localhost:6006"


# ---------------------------------------------------------------------------
# 1. Phoenix Tracing Initialisation
# ---------------------------------------------------------------------------

def init_phoenix_tracing(launch_ui: bool = True) -> bool:
    """
    Start the Phoenix UI server and register the OTel tracer provider so that
    every CrewAI agent span is automatically forwarded to Phoenix.

    Args:
        launch_ui: If True, start the Phoenix web server (default port 6006).

    Returns:
        True if initialisation succeeded, False if Phoenix is unavailable.
    """
    if not PHOENIX_AVAILABLE:
        print("[Phoenix] arize-phoenix not installed. Run: uv add arize-phoenix")
        return False

    try:
        if launch_ui:
            # launch_app() is idempotent — safe to call multiple times
            session = px.launch_app()
            print(f"[Phoenix] UI launched at: {session.url}")

        # Register the OTel tracer that points at Phoenix's OTLP endpoint
        tracer_provider = px_register(
            project_name="loan-processing-crew",
            endpoint=f"{PHOENIX_URL}/v1/traces",
        )

        # Auto-instrument all CrewAI agent/task/tool spans
        CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)
        print("[Phoenix] CrewAI auto-instrumentation active.")
        return True

    except Exception as e:
        print(f"[Phoenix] Initialisation failed: {e}")
        return False


# ---------------------------------------------------------------------------
# 2. Loan-specific LLM-as-Judge Evaluators
# ---------------------------------------------------------------------------

EVAL_RUBRICS = {
    "decision_correctness": {
        "description": "Is the loan decision (APPROVED / REJECTED / ESCALATE) consistent with the applicant's credit score, DTI ratio, and income stated in the output?",
    },
    "compliance_completeness": {
        "description": "Did the agent output explicitly mention compliance with lending regulations such as Equal Credit Opportunity Act (ECOA), Fair Housing Act, or anti-money-laundering (AML) checks?",
    },
    "document_verification": {
        "description": "Does the agent output confirm that identity documents, income documents (pay stubs / W-2), and bank statements were reviewed and validated?",
    },
    "risk_flag_detection": {
        "description": "Were risk flags or fraud signals (if any) correctly identified and cited in the agent's analysis?",
    },
}


def _llm_judge(agent_output: str, rubric_name: str, rubric: dict) -> dict:
    """Run a single LLM-as-judge evaluation against one rubric."""
    if not LITELLM_AVAILABLE:
        return {"score": 0, "label": "UNAVAILABLE", "explanation": "litellm not installed"}

    prompt = f"""You are a strict quality evaluator for an AI-powered loan processing system.

Evaluation Rubric: {rubric['description']}

Agent Output to Evaluate:
---
{agent_output[:3000]}
---

Respond ONLY with a valid JSON object in this exact format:
{{
  "score": <0.0 to 1.0 as a float>,
  "label": "<PASS or FAIL>",
  "explanation": "<one sentence explaining your score>"
}}
"""
    try:
        response = llm_completion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "score": float(result.get("score", 0)),
            "label": str(result.get("label", "FAIL")),
            "explanation": str(result.get("explanation", "")),
        }
    except Exception as e:
        return {"score": 0.0, "label": "ERROR", "explanation": str(e)}


# ---------------------------------------------------------------------------
# 3. Run Evaluations over all Loan Decision Outputs
# ---------------------------------------------------------------------------

def _ensure_eval_db():
    """Create the evaluation results table if it doesn't exist."""
    EVAL_DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(EVAL_DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS eval_results (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluated_at    TEXT,
            application_id  TEXT,
            rubric_name     TEXT,
            score           REAL,
            label           TEXT,
            explanation     TEXT
        )
    """)
    con.commit()
    con.close()


def run_loan_evaluations(application_id: Optional[str] = None) -> pd.DataFrame:
    """
    Run LLM-as-judge evaluations on loan decision output files.

    Args:
        application_id: If given, only evaluate that specific application.
                        If None, evaluate all output files found.

    Returns:
        DataFrame with columns: application_id, rubric_name, score, label, explanation
    """
    _ensure_eval_db()
    output_dir = Path("output")

    # Gather decision files
    if application_id:
        files = [output_dir / f"loan_decision_{application_id}.md"]
        files = [f for f in files if f.exists()]
    else:
        files = list(output_dir.glob("loan_decision_LOAN-*.md"))

    if not files:
        print("[Phoenix Eval] No loan decision files found to evaluate.")
        return pd.DataFrame()

    rows = []
    con = sqlite3.connect(EVAL_DB_PATH)

    for decision_file in files:
        app_id = decision_file.stem.replace("loan_decision_", "")
        agent_output = decision_file.read_text(encoding="utf-8", errors="ignore")
        evaluated_at = datetime.utcnow().isoformat()

        print(f"[Phoenix Eval] Evaluating {app_id} across {len(EVAL_RUBRICS)} rubrics...")

        for rubric_name, rubric in EVAL_RUBRICS.items():
            result = _llm_judge(agent_output, rubric_name, rubric)
            row = {
                "evaluated_at": evaluated_at,
                "application_id": app_id,
                "rubric_name": rubric_name,
                "score": result["score"],
                "label": result["label"],
                "explanation": result["explanation"],
            }
            rows.append(row)

            # Persist to SQLite
            con.execute(
                """INSERT INTO eval_results
                   (evaluated_at, application_id, rubric_name, score, label, explanation)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (row["evaluated_at"], row["application_id"], row["rubric_name"],
                 row["score"], row["label"], row["explanation"]),
            )
        con.commit()

    con.close()
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Load Stored Evaluation Results for the Dashboard
# ---------------------------------------------------------------------------

def get_eval_summary() -> pd.DataFrame:
    """
    Load all evaluation results from the SQLite store.
    Returns a DataFrame ready for display in the Streamlit dashboard.
    """
    _ensure_eval_db()
    try:
        con = sqlite3.connect(EVAL_DB_PATH)
        df = pd.read_sql_query(
            """SELECT application_id, rubric_name, score, label, explanation, evaluated_at
               FROM eval_results
               ORDER BY evaluated_at DESC""",
            con,
        )
        con.close()
        return df
    except Exception:
        return pd.DataFrame()


def clear_eval_results():
    """Wipe all stored evaluation results (useful for re-running from scratch)."""
    _ensure_eval_db()
    con = sqlite3.connect(EVAL_DB_PATH)
    con.execute("DELETE FROM eval_results")
    con.commit()
    con.close()
