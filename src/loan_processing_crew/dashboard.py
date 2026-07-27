import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pypdf
from litellm import completion
try:
    from loan_processing_crew.phoenix_eval import (
        run_loan_evaluations, get_eval_summary, clear_eval_results, PHOENIX_AVAILABLE
    )
except Exception:
    PHOENIX_AVAILABLE = False
    def get_eval_summary(): import pandas as pd; return pd.DataFrame()
    def run_loan_evaluations(application_id=None): import pandas as pd; return pd.DataFrame()
    def clear_eval_results(): pass

# 1. Page Configuration
st.set_page_config(
    page_title="Loan Processing Agent Observability",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. Theme Toggle State
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

IS_DARK = st.session_state.theme == "dark"

# 3. CSS Design System
# Color variables mapped based on theme
THEME_CSS = f"""
<style>
:root {{
    --bg: {"#09090b" if IS_DARK else "#ffffff"};
    --bg-subtle: {"#0c0c0f" if IS_DARK else "#f9fafb"};
    --card: {"#0c0c0f" if IS_DARK else "#ffffff"};
    --card-hover: {"#131316" if IS_DARK else "#f4f4f5"};
    --border: {"#1e1e24" if IS_DARK else "#e4e4e7"};
    --border-subtle: {"#16161a" if IS_DARK else "#f0f0f2"};
    --text: {"#fafafa" if IS_DARK else "#09090b"};
    --text-muted: #71717a;
    --text-dim: {"#52525b" if IS_DARK else "#a1a1aa"};
    --accent: #2563eb;
    --accent-muted: #1d4ed8;
    --green: {"#22c55e" if IS_DARK else "#16a34a"};
    --green-muted: {"rgba(34,197,94,0.12)" if IS_DARK else "rgba(22,163,74,0.08)"};
    --red: {"#ef4444" if IS_DARK else "#dc2626"};
    --red-muted: {"rgba(239,68,68,0.12)" if IS_DARK else "rgba(220,38,38,0.08)"};
    --amber: {"#f59e0b" if IS_DARK else "#d97706"};
    --amber-muted: {"rgba(245,158,11,0.12)" if IS_DARK else "rgba(217,119,6,0.08)"};
    --shadow: {"none" if IS_DARK else "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)"};
    --radius: 10px;
}}

/* Hide Streamlit chrome */
header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton,
div[data-testid="stSidebarCollapsedControl"] {{
    display: none !important;
}}

/* Global App Styling */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {{
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', -apple-system, sans-serif !important;
}}
.block-container {{
    padding: 1.5rem 2rem 2rem !important;
    max-width: 1360px !important;
}}

/* Brand Styling */
.brand {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 0.5rem;
}}
.brand-icon {{
    font-size: 1.5rem;
    color: var(--accent);
}}
.brand-name {{
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text);
}}

/* Metrics Grid Gap */
[data-testid="stHorizontalBlock"] {{ gap: 1.25rem !important; }}
[data-testid="stVerticalBlock"] > div:has(> [data-testid="stHorizontalBlock"]) {{
    margin-bottom: 0.5rem !important;
}}

/* Metric Card */
.metric-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.1rem 1.25rem;
    box-shadow: var(--shadow);
}}
.metric-label {{
    font-size: 0.76rem;
    color: var(--text-muted);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.metric-value {{
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -0.03em;
    margin-top: 0.25rem;
}}
.metric-delta {{
    font-size: 0.72rem;
    font-weight: 500;
    margin-top: 0.35rem;
    padding: 2px 8px;
    border-radius: 6px;
    display: inline-flex;
    align-items: center;
    gap: 3px;
}}
.delta-up {{ color: var(--green); background: var(--green-muted); }}
.delta-down {{ color: var(--red); background: var(--red-muted); }}
.delta-warn {{ color: var(--amber); background: var(--amber-muted); }}

/* Card Wrapping */
.chart-wrap {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem;
    box-shadow: var(--shadow);
    margin-bottom: 1.25rem;
}}
.chart-title {{
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.2rem;
}}
.chart-subtitle {{
    font-size: 0.72rem;
    color: var(--text-dim);
    margin-bottom: 0.9rem;
}}

/* Tabs Styling */
button[data-baseweb="tab"] {{
    background: transparent !important;
    color: var(--text-muted) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.5rem 1rem !important;
    border: 1px solid transparent !important;
    border-radius: 7px !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: var(--text) !important;
    background: var(--card) !important;
    border-color: var(--border) !important;
}}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{
    display: none !important;
}}
[data-baseweb="tab-list"] {{
    gap: 4px !important;
    background: var(--bg-subtle) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 3px;
}}

/* Custom Data Table */
.data-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.8rem;
    margin-top: 0.5rem;
}}
.data-table th {{
    text-align: left;
    padding: 0.6rem 0.8rem;
    color: var(--text-muted);
    font-weight: 65536;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
}}
.data-table td {{
    padding: 0.65rem 0.8rem;
    color: var(--text);
    border-bottom: 1px solid var(--border-subtle);
}}
.data-table tr:hover td {{
    background-color: var(--card-hover);
}}
.data-table tr:last-child td {{
    border-bottom: none;
}}

/* Status Badges */
.badge {{
    display: inline-block;
    padding: 2px 9px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
}}
.badge-green {{ color: var(--green); background: var(--green-muted); }}
.badge-red {{ color: var(--red); background: var(--red-muted); }}
.badge-amber {{ color: var(--amber); background: var(--amber-muted); }}
.badge-blue {{ color: var(--accent); background: rgba(37,99,235,0.1); }}
.badge-gray {{ color: var(--text-muted); background: var(--border); }}

/* Preformatted detail block */
.detail-block {{
    background-color: var(--bg-subtle);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: var(--text);
    white-space: pre-wrap;
    overflow-x: auto;
    margin-top: 0.5rem;
}}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)

# 4. Plotly Chart Theming
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#71717a" if not IS_DARK else "#a1a1aa", size=11),
    margin=dict(l=10, r=10, t=25, b=10),
    xaxis=dict(
        gridcolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        zerolinecolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        tickfont=dict(size=10, color="#71717a"),
    ),
    yaxis=dict(
        gridcolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        zerolinecolor="rgba(0,0,0,0.04)" if not IS_DARK else "rgba(255,255,255,0.04)",
        tickfont=dict(size=10, color="#71717a"),
    ),
)

# Helpers for database interactions
DB_PATH = Path("output") / "telemetry.db"

def get_db_connection():
    if not DB_PATH.exists():
        # Create table headers so streamlit works even if db is empty
        conn = sqlite3.connect(DB_PATH)
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
        return conn
    return sqlite3.connect(DB_PATH)

def load_data():
    conn = get_db_connection()
    spans_df = pd.read_sql_query("SELECT * FROM spans", conn)
    audit_df = pd.read_sql_query("SELECT * FROM audit_logs", conn)
    conn.close()
    return spans_df, audit_df

# UI Header
head_left, head_right = st.columns([8, 1])
with head_left:
    st.markdown("""
    <div class="brand">
        <span class="brand-icon">◆</span>
        <span class="brand-name">LendTrace Observability Dashboard</span>
    </div>
    """, unsafe_allow_html=True)
with head_right:
    theme_label = "☀️ Light" if IS_DARK else "🌙 Dark"
    st.button(theme_label, on_click=toggle_theme, use_container_width=True)

# Main Navigation Tabs
tab_overview, tab_traces, tab_intake, tab_eval = st.tabs([
    "📊 Executive Summary",
    "🔍 Trace Inspector & Compliance",
    "📝 New Application Form",
    "🧪 Evaluation",
])

spans_df, audit_df = load_data()

if spans_df.empty:
    st.info("No traces found in the database. Please run a loan processing flow to populate telemetry.")
else:
    # Process attributes to parse out JSON
    def parse_attributes(attr_str):
        try:
            return json.loads(attr_str) if attr_str else {}
        except Exception:
            return {}

    spans_df["parsed_attrs"] = spans_df["attributes"].apply(parse_attributes)

    # Resolve Verification Status for workflows
    crew_spans = spans_df[spans_df["type"] == "crew"].copy()
    
    def get_verification_status(row):
        attrs = row["parsed_attrs"]
        return attrs.get("loan.verification_status", "UNKNOWN")

    if not crew_spans.empty:
        crew_spans["verification_status"] = crew_spans.apply(get_verification_status, axis=1)
    else:
        crew_spans["verification_status"] = []

    # Map application_id to verification_status
    app_status_map = dict(zip(crew_spans["application_id"], crew_spans["verification_status"]))
    
    # ---------------- TAB 1: EXECUTIVE OVERVIEW ----------------
    with tab_overview:
        # Calculate summary metrics
        total_runs = crew_spans["application_id"].nunique() if not crew_spans.empty else 0
        total_tokens = spans_df["total_tokens"].sum()
        total_cost = spans_df["cost"].sum()
        avg_latency = (crew_spans["duration_ms"].mean() / 1000.0) if not crew_spans.empty else 0.0
        
        # Calculate error rates (failed workflows)
        failed_runs = crew_spans[crew_spans["status"] == "ERROR"].shape[0] if not crew_spans.empty else 0
        error_rate = (failed_runs / total_runs * 100.0) if total_runs > 0 else 0.0

        # KPI Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Processed Applications</div>
                <div class="metric-value">{total_runs}</div>
                <div class="metric-delta delta-up">⚡ active store</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Accumulated LLM Costs</div>
                <div class="metric-value">${total_cost:.5f}</div>
                <div class="metric-delta delta-warn">◆ {total_tokens:,} tokens</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg Agent Latency</div>
                <div class="metric-value">{avg_latency:.2f}s</div>
                <div class="metric-delta delta-up">↓ optimized paths</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            delta_class = "delta-up" if error_rate == 0 else "delta-down"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Agent Error Rate</div>
                <div class="metric-value">{error_rate:.1f}%</div>
                <div class="metric-delta {delta_class}">⚠ {failed_runs} exceptions</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Charts Section
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("""
            <div class="chart-wrap">
                <div class="chart-title">Verification Outcome Distribution</div>
                <div class="chart-subtitle">Lending decision tier counts from downstream compliance/underwriting.</div>
            """, unsafe_allow_html=True)
            
            if not crew_spans.empty:
                outcome_counts = crew_spans["verification_status"].value_counts().reset_index()
                outcome_counts.columns = ["Status", "Count"]
                
                # Apply custom styling colors
                color_map = {
                    "APPROVED": "#22c55e",
                    "CONDITIONALLY APPROVED": "#f59e0b",
                    "DECLINED": "#ef4444",
                    "FAILED": "#71717a",
                    "COMPLETED": "#2563eb"
                }
                
                fig = px.bar(
                    outcome_counts, 
                    x="Status", 
                    y="Count", 
                    color="Status",
                    color_discrete_map=color_map,
                    text_auto=True
                )
                fig.update_layout(PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.write("No execution outcomes recorded.")
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="chart-wrap">
                <div class="chart-title">Workflow Execution Latency</div>
                <div class="chart-subtitle">Total processing time in seconds mapped to individual loan applications.</div>
            """, unsafe_allow_html=True)
            
            if not crew_spans.empty:
                lat_df = crew_spans.copy()
                lat_df["duration_sec"] = lat_df["duration_ms"] / 1000.0
                
                fig = px.bar(
                    lat_df, 
                    x="application_id", 
                    y="duration_sec",
                    labels={"application_id": "Application ID", "duration_sec": "Duration (sec)"},
                    color_discrete_sequence=["#2563eb"]
                )
                fig.update_layout(PLOT_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.write("No latency metrics recorded.")
            st.markdown("</div>", unsafe_allow_html=True)

        # Run History Table
        st.markdown("""
        <div class="chart-wrap">
            <div class="chart-title">Loan Processing Workflow History</div>
            <div class="chart-subtitle">History of executed workflows, execution stats, and outcome decisions.</div>
        """, unsafe_allow_html=True)

        # Construct run history rows
        table_rows = ""
        for _, row in crew_spans.sort_values("start_time", ascending=False).iterrows():
            app_id = row["application_id"]
            raw_status = row["status"]
            v_status = app_status_map.get(app_id, "UNKNOWN")
            
            # Badge styles
            badge_class = "badge-gray"
            if v_status == "APPROVED":
                badge_class = "badge-green"
            elif v_status == "CONDITIONALLY APPROVED":
                badge_class = "badge-amber"
            elif v_status in ["DECLINED", "FAILED"]:
                badge_class = "badge-red"
            elif v_status == "COMPLETED":
                badge_class = "badge-blue"

            # Compute trace stats
            trace_spans = spans_df[spans_df["trace_id"] == row["trace_id"]]
            tokens_sum = trace_spans["total_tokens"].sum()
            cost_sum = trace_spans["cost"].sum()
            latency_sec = row["duration_ms"] / 1000.0
            
            formatted_date = ""
            if row["start_time"]:
                try:
                    dt = datetime.fromisoformat(row["start_time"])
                    formatted_date = dt.strftime("%b %d, %Y %H:%M:%S")
                except Exception:
                    formatted_date = row["start_time"]

            table_rows += f"""
            <tr>
                <td><b>{app_id}</b></td>
                <td><span class="badge {badge_class}">{v_status}</span></td>
                <td>{latency_sec:.2f}s</td>
                <td>{tokens_sum:,}</td>
                <td>${cost_sum:.5f}</td>
                <td>{formatted_date}</td>
            </tr>
            """

        st.markdown(f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Application ID</th>
                    <th>Decision Status</th>
                    <th>Workflow Latency</th>
                    <th>Tokens</th>
                    <th>LLM Cost</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- TAB 2: TRACE INSPECTOR & COMPLIANCE ----------------
    with tab_traces:
        # Load unique application IDs for selection
        available_apps = spans_df["application_id"].dropna().unique().tolist()
        if "unknown" in available_apps:
            available_apps.remove("unknown")
        
        # Selection widgets
        col_sel1, col_sel2 = st.columns([1, 2])
        with col_sel1:
            selected_app_id = st.selectbox("Select Loan Application to Inspect", available_apps)
        
        if selected_app_id:
            # Load all spans for this application
            app_spans = spans_df[spans_df["application_id"] == selected_app_id].copy()
            app_crew_span = app_spans[app_spans["type"] == "crew"].iloc[0] if not app_spans[app_spans["type"] == "crew"].empty else None
            
            # Status summary headers
            v_status = app_status_map.get(selected_app_id, "UNKNOWN")
            badge_class = "badge-gray"
            if v_status == "APPROVED":
                badge_class = "badge-green"
            elif v_status == "CONDITIONALLY APPROVED":
                badge_class = "badge-amber"
            elif v_status in ["DECLINED", "FAILED"]:
                badge_class = "badge-red"
            elif v_status == "COMPLETED":
                badge_class = "badge-blue"

            st.markdown(f"""
            <div class="chart-wrap" style="padding: 1rem 1.2rem; margin-bottom: 0.75rem;">
                <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: 500;">Workflow Decision for {selected_app_id}: </span>
                <span class="badge {badge_class}" style="font-size: 0.8rem; margin-left: 5px;">{v_status}</span>
            </div>
            """, unsafe_allow_html=True)

            # Columns for Timeline and Audits
            t_col1, t_col2 = st.columns([7, 3])

            with t_col1:
                st.markdown("""
                <div class="chart-wrap">
                    <div class="chart-title">End-to-End Tracing Timeline</div>
                    <div class="chart-subtitle">Gantt visualization of active execution spans (tasks, tools, LLM completions).</div>
                """, unsafe_allow_html=True)

                if not app_spans.empty:
                    # Sort spans by start_time
                    app_spans = app_spans.sort_values("start_time").copy()
                    
                    # Convert start_time and end_time to milliseconds relative to trace start
                    min_start = pd.to_datetime(app_spans["start_time"]).min()
                    app_spans["start_dt"] = pd.to_datetime(app_spans["start_time"])
                    app_spans["end_dt"] = pd.to_datetime(app_spans["end_time"])
                    
                    app_spans["rel_start_ms"] = (app_spans["start_dt"] - min_start).dt.total_seconds() * 1000.0
                    app_spans["duration_ms_calc"] = (app_spans["end_dt"] - app_spans["start_dt"]).dt.total_seconds() * 1000.0
                    
                    # Create names with indentation for visual nesting
                    # crew is root, task is indented, tool and llm are double indented
                    def format_nesting(row):
                        indent = ""
                        if row["type"] == "task":
                            indent = " ↳ "
                        elif row["type"] in ["tool", "llm"]:
                            indent = "     ↳ "
                        name = row["name"]
                        if name.startswith("tool:"):
                            name = f"🔧 {name[5:]}"
                        elif name == "llm_completion":
                            name = "🤖 LLM Completion"
                        elif row["type"] == "crew":
                            name = "🚀 Crew Execution"
                        return f"{indent}{name}"
                    
                    app_spans["display_name"] = app_spans.apply(format_nesting, axis=1)

                    # Build horizontal Gantt bar using Plotly
                    fig = go.Figure()
                    
                    # Color map by type
                    type_colors = {
                        "crew": "#2563eb",
                        "task": "#93c5fd",
                        "tool": "#f59e0b",
                        "llm": "#10b981",
                        "unknown": "#71717a"
                    }

                    # We plot each span
                    # To ensure they render top-to-bottom in start sequence, reverse dataframe order
                    plot_df = app_spans.iloc[::-1]
                    
                    for idx, row in plot_df.iterrows():
                        span_color = type_colors.get(row["type"], "#71717a")
                        fig.add_trace(go.Bar(
                            y=[row["display_name"]],
                            x=[row["duration_ms_calc"] / 1000.0],
                            base=[row["rel_start_ms"] / 1000.0],
                            orientation='h',
                            marker=dict(color=span_color, line=dict(color="rgba(0,0,0,0)", width=0)),
                            hoverinfo="text",
                            text=f"{row['name']} ({row['duration_ms'] / 1000.0:.2f}s)",
                            textposition="inside",
                            showlegend=False
                        ))
                    
                    layout = PLOT_LAYOUT.copy()
                    layout["xaxis"]["title"] = "Elapsed Time (seconds)"
                    layout["yaxis"]["tickmode"] = "array"
                    fig.update_layout(layout)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.write("No spans found to trace.")
                st.markdown("</div>", unsafe_allow_html=True)

            with t_col2:
                st.markdown("""
                <div class="chart-wrap">
                    <div class="chart-title">Compliance Audit Logs</div>
                    <div class="chart-subtitle">Regulatory checks performed under TILA, ECOA, and internal checks.</div>
                """, unsafe_allow_html=True)

                app_audits = audit_df[audit_df["application_id"] == selected_app_id]
                
                if app_audits.empty:
                    st.write("No compliance audits triggered yet for this run.")
                else:
                    for _, audit_row in app_audits.iterrows():
                        status = audit_row["status"].upper()
                        badge_style = "badge-gray"
                        if "PASS" in status:
                            badge_style = "badge-green"
                        elif "FAIL" in status:
                            badge_style = "badge-red"
                        elif "WARNING" in status or "REQUIRED" in status or "CAUTION" in status:
                            badge_style = "badge-amber"
                            
                        st.markdown(f"""
                        <div style="border-bottom: 1px solid var(--border-subtle); padding: 0.5rem 0;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 0.8rem; font-weight: 600;">{audit_row['check_name']}</span>
                                <span class="badge {badge_style}">{status}</span>
                            </div>
                            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">
                                {audit_row['detail']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Details Inspector Section
            st.markdown("""
            <div class="chart-wrap">
                <div class="chart-title">Span Attribute Inspector</div>
                <div class="chart-subtitle">Select an execution span from the trace hierarchy to view OpenTelemetry attributes, metrics, inputs, and outputs.</div>
            """, unsafe_allow_html=True)

            # Dropdown list of spans for selection
            span_options = dict(zip(app_spans["name"] + " (" + app_spans["type"] + ")", app_spans["span_id"]))
            selected_span_label = st.selectbox("Select Span to Inspect", list(span_options.keys()))
            
            if selected_span_label:
                selected_span_id = span_options[selected_span_label]
                span_detail = app_spans[app_spans["span_id"] == selected_span_id].iloc[0]
                
                # Show key metrics in 4 columns
                d1, d2, d3, d4 = st.columns(4)
                with d1:
                    st.metric("Span Name", span_detail["name"])
                with d2:
                    st.metric("Duration", f"{span_detail['duration_ms'] / 1000.0:.3f}s")
                with d3:
                    st.metric("Status", span_detail["status"])
                with d4:
                    cost_val = span_detail["cost"]
                    st.metric("Tokens / Cost", f"{span_detail['total_tokens']:,} / ${cost_val:.5f}" if span_detail["total_tokens"] > 0 else "0 / $0.00000")

                # Show details based on type
                st.markdown("### Context Arguments & Payloads")
                
                # Tool arguments/output
                if span_detail["type"] == "tool":
                    args_val = span_detail["parsed_attrs"].get("tool.args", "")
                    output_val = span_detail["parsed_attrs"].get("tool.output_preview", "")
                    st.markdown("**Tool Arguments (Input)**")
                    st.markdown(f'<div class="detail-block">{args_val}</div>', unsafe_allow_html=True)
                    st.markdown("**Tool Output (Result)**")
                    st.markdown(f'<div class="detail-block">{output_val}</div>', unsafe_allow_html=True)

                # Task output
                elif span_detail["type"] == "task":
                    output_val = span_detail["parsed_attrs"].get("task.output_preview", "")
                    st.markdown("**Task Output Summary**")
                    st.markdown(f'<div class="detail-block">{output_val}</div>', unsafe_allow_html=True)

                # LLM system/attributes
                elif span_detail["type"] == "llm":
                    req_model = span_detail["parsed_attrs"].get("gen_ai.request.model", "")
                    res_model = span_detail["parsed_attrs"].get("gen_ai.response.model", "")
                    st.write(f"- **Request Model**: `{req_model}`")
                    st.write(f"- **Response Model**: `{res_model}`")

                # Show raw attributes
                st.markdown("### Raw OpenTelemetry Attributes")
                st.markdown(f'<div class="detail-block">{json.dumps(span_detail["parsed_attrs"], indent=2)}</div>', unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

# ----------------- Tab 3: New Application Intake Form -----------------
with tab_intake:
    st.markdown("""
    <div class="chart-wrap">
        <div class="chart-title">Intake New Loan Application</div>
        <div class="chart-subtitle">Upload applicant documents to pre-populate the profile, or enter the details manually.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Document Uploader section
    st.markdown("### 📂 Upload Supporting Documents")
    st.caption("Upload text-based PDF, TXT, or JSON files (e.g., pay stubs, bank statements, tax forms, or personal info sheets) to auto-extract application fields.")
    
    uploaded_files = st.file_uploader(
        "Upload Files",
        accept_multiple_files=True,
        type=["pdf", "txt", "json"],
        key="document_uploader"
    )
    
    if uploaded_files:
        if st.button("🔍 Extract Data from Uploaded Documents", key="extract_doc_btn"):
            with st.spinner("Extracting content and parsing structured loan data..."):
                # Create raw_documents directory and a temporary directory
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                temp_app_id = f"LOAN-TEMP-{timestamp}"
                raw_dir = Path("raw_documents") / temp_app_id
                raw_dir.mkdir(parents=True, exist_ok=True)
                
                # Save uploaded files and compile text content
                all_text_content = []
                saved_files_info = []
                
                for file in uploaded_files:
                    file_path = raw_dir / file.name
                    file_bytes = file.read()
                    with open(file_path, "wb") as f:
                        f.write(file_bytes)
                    saved_files_info.append(file.name)
                    
                    # Extract text based on file type
                    ext = file.name.split(".")[-1].lower()
                    if ext == "pdf":
                        try:
                            pdf_reader = pypdf.PdfReader(file_path)
                            pdf_text = []
                            for idx, page in enumerate(pdf_reader.pages):
                                txt = page.extract_text()
                                if txt:
                                    pdf_text.append(txt)
                            all_text_content.append(f"--- START PDF: {file.name} ---\n" + "\n".join(pdf_text) + f"\n--- END PDF: {file.name} ---")
                        except Exception as e:
                            all_text_content.append(f"[Error parsing PDF {file.name}: {e}]")
                    elif ext == "txt" or ext == "json":
                        try:
                            txt = file_bytes.decode("utf-8", errors="ignore")
                            all_text_content.append(f"--- START FILE: {file.name} ---\n{txt}\n--- END FILE: {file.name} ---")
                        except Exception as e:
                            all_text_content.append(f"[Error parsing text file {file.name}: {e}]")
                            
                # Combine all extracted text
                combined_document_text = "\n\n".join(all_text_content)
                
                # Invoke LLM to extract fields
                system_prompt = (
                    "You are a structured document parsing engine for personal loan intake. "
                    "Analyze the provided raw document text and extract all relevant information to populate the application form. "
                    "You must output a JSON object containing the fields below. Do not add any conversational text or formatting wrappers like ```json. "
                    "Format the JSON with the following schema:\n"
                    "{\n"
                    "  \"full_name\": \"Applicant's full name\",\n"
                    "  \"date_of_birth\": \"YYYY-MM-DD format (if found)\",\n"
                    "  \"ssn_last_four\": \"4 digit string\",\n"
                    "  \"email\": \"email address\",\n"
                    "  \"phone\": \"phone number\",\n"
                    "  \"street\": \"residential street address\",\n"
                    "  \"city\": \"city\",\n"
                    "  \"state\": \"2 letter state code\",\n"
                    "  \"zip\": \"ZIP code\",\n"
                    "  \"employer\": \"employer name\",\n"
                    "  \"position\": \"job title\",\n"
                    "  \"years_employed\": float (years at current job),\n"
                    "  \"annual_salary\": float (annual salary in USD),\n"
                    "  \"employment_type\": \"Full-Time\" | \"Part-Time\" | \"Self-Employed\" | \"Contract\" | \"Unemployed\",\n"
                    "  \"credit_score\": int (300-850, if not found use 700),\n"
                    "  \"monthly_debt_payments\": float (monthly payment on other debts),\n"
                    "  \"monthly_housing_cost\": float (rent or mortgage payment),\n"
                    "  \"checking_account_balance\": float,\n"
                    "  \"savings_account_balance\": float,\n"
                    "  \"existing_loans\": [\n"
                    "    { \"type\": \"Auto Loan\"|\"Student Loan\"|\"Personal Loan\"|\"Credit Card Debt\", \"remaining_balance\": float, \"monthly_payment\": float }\n"
                    "  ],\n"
                    "  \"bankruptcies\": int (number of bankruptcies),\n"
                    "  \"late_payments_last_24_months\": int,\n"
                    "  \"loan_amount\": float (requested loan amount),\n"
                    "  \"loan_purpose\": \"Debt Consolidation\" | \"Home Improvement\" | \"Medical Bills\" | \"Major Purchase\" | \"Other\",\n"
                    "  \"requested_term_months\": int (loan term in months, e.g. 36),\n"
                    "  \"preferred_rate_type\": \"Fixed\" | \"Variable\"\n"
                    "}"
                )
                
                try:
                    response = completion(
                        model=os.environ.get("OPENAI_MODEL_NAME", "gpt-4o"),
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Here is the text extracted from the uploaded files:\n\n{combined_document_text}"}
                        ],
                        response_format={"type": "json_object"}
                    )
                    
                    raw_json = response.choices[0].message.content
                    extracted_data = json.loads(raw_json)
                    
                    # Generate the final application ID based on Name + Timestamp
                    full_name_extracted = extracted_data.get("full_name", "UNKNOWN").strip()
                    cleaned_name = "".join(c for c in full_name_extracted.upper() if c.isalnum() or c == " ").strip()
                    cleaned_name = cleaned_name.replace(" ", "_")
                    if not cleaned_name:
                        cleaned_name = "APPLICANT"
                        
                    final_app_id = f"LOAN-{cleaned_name}-{timestamp}"
                    
                    # Rename the directory to the final application ID
                    final_dir = Path("raw_documents") / final_app_id
                    if raw_dir.exists():
                        raw_dir.rename(final_dir)
                    
                    # Save files info and final app ID to the state
                    st.session_state.temp_raw_dir = str(final_dir)
                    st.session_state.temp_app_id = final_app_id
                    st.session_state.extracted_data = extracted_data
                    
                    st.success(f"Success! Data extracted for '{full_name_extracted}'. Application ID: {final_app_id}")
                    st.rerun()
                except Exception as err:
                    st.error(f"Failed to parse documents using LLM: {err}")
                    
    st.markdown("---")
    
    # Load extracted data if available, and sanitize all numeric fields
    ext_data = st.session_state.get("extracted_data", {})

    # Sanitize: clamp numeric values to their widget bounds so Streamlit never crashes
    def _clamp(val, lo, hi, default):
        try:
            v = float(val)
            if v < lo or v > hi:
                return default
            return v
        except (TypeError, ValueError):
            return default

    if ext_data:
        ext_data["loan_amount"]              = _clamp(ext_data.get("loan_amount", 50000.0),      500.0,   50_000_000.0, 50000.0)
        ext_data["annual_salary"]            = _clamp(ext_data.get("annual_salary", 250000.0),    0.0,   100_000_000.0, 250000.0)
        ext_data["years_employed"]           = _clamp(ext_data.get("years_employed", 10.0),       0.0,           50.0, 10.0)
        ext_data["credit_score"]             = int(_clamp(ext_data.get("credit_score", 750),     300,            850, 750))
        ext_data["checking_account_balance"] = _clamp(ext_data.get("checking_account_balance", 50000.0), 0.0, 100_000_000.0, 50000.0)
        ext_data["savings_account_balance"]  = _clamp(ext_data.get("savings_account_balance", 1000000.0), 0.0, 100_000_000.0, 1000000.0)
        ext_data["monthly_housing_cost"]     = _clamp(ext_data.get("monthly_housing_cost", 2500.0), 0.0,      100_000.0, 2500.0)
        ext_data["requested_term_months"]    = int(_clamp(ext_data.get("requested_term_months", 36), 6,              120, 36))


    st.markdown("### ✍️ Review and Edit Application Form")
    st.caption("Review the extracted data below. You can make adjustments to any field before submitting.")
    
    with st.form("loan_intake_form", clear_on_submit=False):
        st.markdown("#### 1. Applicant Profile")
        col1, col2 = st.columns(2)
        with col1:
            default_name = ext_data.get("full_name", "")
            full_name = st.text_input("Full Name", value=default_name, placeholder="e.g. Bruce Wayne")
            
            # Date of Birth conversion
            default_dob = datetime(1990, 1, 1).date()
            dob_str = ext_data.get("date_of_birth", "")
            if dob_str:
                try:
                    default_dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except Exception:
                    pass
            dob = st.date_input("Date of Birth", value=default_dob)
            
            default_ssn = ext_data.get("ssn_last_four", "")
            ssn_last_four = st.text_input("SSN Last 4 Digits", value=default_ssn, max_chars=4, placeholder="e.g. 1234")
        with col2:
            default_email = ext_data.get("email", "")
            email = st.text_input("Email Address", value=default_email, placeholder="e.g. bruce.wayne@email.com")
            
            default_phone = ext_data.get("phone", "")
            phone = st.text_input("Phone Number", value=default_phone, placeholder="e.g. 555-0199")
            
        st.markdown("**Residential Address**")
        col_street, col_city, col_state, col_zip = st.columns([2, 1, 1, 1])
        with col_street:
            default_street = ext_data.get("street", "")
            street = st.text_input("Street Address", value=default_street, placeholder="e.g. 1007 Mountain Drive")
        with col_city:
            default_city = ext_data.get("city", "")
            city = st.text_input("City", value=default_city, placeholder="e.g. Gotham")
        with col_state:
            default_state = ext_data.get("state", "")
            state = st.text_input("State", value=default_state, max_chars=2, placeholder="e.g. NJ")
        with col_zip:
            default_zip = ext_data.get("zip", "")
            zip_code = st.text_input("ZIP Code", value=default_zip, placeholder="e.g. 07001")
            
        st.markdown("---")
        st.markdown("#### 2. Employment & Income")
        col3, col4 = st.columns(2)
        with col3:
            default_employer = ext_data.get("employer", "")
            employer = st.text_input("Employer / Organization", value=default_employer, placeholder="e.g. Wayne Enterprises")
            
            default_position = ext_data.get("position", "")
            position = st.text_input("Job Title / Position", value=default_position, placeholder="e.g. Chairman & CEO")
            
            default_years = max(0.0, float(ext_data.get("years_employed", 10.0)))
            years_employed = st.number_input("Years Employed", min_value=0.0, max_value=50.0, value=default_years, step=0.1)
        with col4:
            default_salary = max(0.0, float(ext_data.get("annual_salary", 250000.0)))
            annual_salary = st.number_input("Annual Salary ($)", min_value=0.0, max_value=100000000.0, value=default_salary, step=5000.0)
            
            default_emp_type = ext_data.get("employment_type", "Full-Time")
            if default_emp_type not in ["Full-Time", "Part-Time", "Self-Employed", "Contract", "Unemployed"]:
                default_emp_type = "Full-Time"
            employment_type = st.selectbox("Employment Type", ["Full-Time", "Part-Time", "Self-Employed", "Contract", "Unemployed"], index=["Full-Time", "Part-Time", "Self-Employed", "Contract", "Unemployed"].index(default_emp_type))
            
        st.markdown("---")
        st.markdown("#### 3. Financial Profile & Debts")
        col5, col6 = st.columns(2)
        with col5:
            default_credit = max(300, min(850, int(ext_data.get("credit_score", 750))))
            credit_score = st.number_input("Credit Score", min_value=300, max_value=850, value=default_credit)
            
            default_checking = max(0.0, float(ext_data.get("checking_account_balance", 50000.0)))
            checking_balance = st.number_input("Checking Account Balance ($)", min_value=0.0, max_value=100000000.0, value=default_checking, step=1000.0)
            
            default_savings = max(0.0, float(ext_data.get("savings_account_balance", 1000000.0)))
            savings_balance = st.number_input("Savings Account Balance ($)", min_value=0.0, max_value=100000000.0, value=default_savings, step=5000.0)
        with col6:
            default_housing = max(0.0, float(ext_data.get("monthly_housing_cost", 2500.0)))
            monthly_housing_cost = st.number_input("Monthly Housing Cost (Rent/Mortgage) ($)", min_value=0.0, max_value=100000.0, value=default_housing, step=100.0)
            
            default_bankruptcies = int(ext_data.get("bankruptcies", 0))
            bankruptcies = st.number_input("Bankruptcies (Lifetime)", min_value=0, max_value=10, value=default_bankruptcies)
            
            default_late = int(ext_data.get("late_payments_last_24_months", 0))
            late_payments = st.number_input("Late Payments (Last 24 Months)", min_value=0, max_value=50, value=default_late)
            
        st.markdown("**Existing Loans / Monthly Liabilities**")
        
        # Load existing loan from extracted data if available
        ext_loans = ext_data.get("existing_loans", [])
        default_loan_type = "None"
        default_loan_bal = 0.0
        default_loan_pay = 0.0
        if ext_loans and isinstance(ext_loans, list) and len(ext_loans) > 0:
            first_loan = ext_loans[0]
            if isinstance(first_loan, dict):
                default_loan_type = first_loan.get("type", "None")
                default_loan_bal = float(first_loan.get("remaining_balance", 0.0))
                default_loan_pay = float(first_loan.get("monthly_payment", 0.0))
            
        col_loan_type, col_loan_bal, col_loan_pay = st.columns([2, 2, 2])
        with col_loan_type:
            loan_types_list = ["None", "Auto Loan", "Student Loan", "Personal Loan", "Credit Card Debt"]
            if default_loan_type not in loan_types_list:
                default_loan_type = "None"
            loan_type = st.selectbox("Existing Loan Type", loan_types_list, index=loan_types_list.index(default_loan_type))
        with col_loan_bal:
            loan_bal = st.number_input("Remaining Loan Balance ($)", min_value=0.0, max_value=10000000.0, value=default_loan_bal, step=500.0)
        with col_loan_pay:
            loan_pay = st.number_input("Monthly Loan Payment ($)", min_value=0.0, max_value=100000.0, value=default_loan_pay, step=50.0)

        st.markdown("---")
        st.markdown("#### 4. Loan Request")
        col7, col8 = st.columns(2)
        with col7:
            default_req_amt = max(500.0, float(ext_data.get("loan_amount", 50000.0)))
            loan_amount = st.number_input("Requested Loan Amount ($)", min_value=500.0, max_value=50000000.0, value=default_req_amt, step=5000.0)
            
            default_purpose = ext_data.get("loan_purpose", "Debt Consolidation")
            purpose_list = ["Debt Consolidation", "Home Improvement", "Medical Bills", "Major Purchase", "Other"]
            if default_purpose not in purpose_list:
                default_purpose = "Other"
            loan_purpose = st.selectbox("Loan Purpose", purpose_list, index=purpose_list.index(default_purpose))
        with col8:
            default_term = max(6, min(120, int(ext_data.get("requested_term_months", 36))))
            requested_term = st.number_input("Requested Term (Months)", min_value=6, max_value=120, value=default_term, step=1)
            
            default_rate_type = ext_data.get("preferred_rate_type", "Fixed")
            rate_types_list = ["Fixed", "Variable"]
            if default_rate_type not in rate_types_list:
                default_rate_type = "Fixed"
            preferred_rate_type = st.selectbox("Rate Type Preference", rate_types_list, index=rate_types_list.index(default_rate_type))
            
        st.markdown("---")
        st.markdown("#### 5. Document Intake Verification")
        # Check standard documents submitted
        docs_submitted_list = ext_data.get("documents_submitted", [])
        
        col_doc1, col_doc2 = st.columns(2)
        with col_doc1:
            doc_id = st.checkbox("Government-issued Photo ID (Driver's License)", value=any("ID" in str(d) or "License" in str(d) for d in docs_submitted_list) or True)
            doc_pay = st.checkbox("Last 3 months pay stubs", value=any("pay stub" in str(d).lower() or "salary" in str(d).lower() for d in docs_submitted_list) or True)
            doc_w2 = st.checkbox("W-2 forms (2024, 2025)", value=any("W-2" in str(d) or "tax" in str(d).lower() for d in docs_submitted_list) or True)
        with col_doc2:
            doc_bank = st.checkbox("Bank statements (last 3 months)", value=any("bank statement" in str(d).lower() for d in docs_submitted_list) or True)
            doc_emp = st.checkbox("Employment verification letter", value=any("employment verification" in str(d).lower() or "employer letter" in str(d).lower() for d in docs_submitted_list) or True)
            
        submit_btn = st.form_submit_button("Create Loan Application Record")

    if submit_btn:
        if not full_name.strip():
            st.error("Please enter the applicant's full name.")
        else:
            cleaned_name = "".join(c for c in full_name.upper() if c.isalnum() or c == " ").strip()
            cleaned_name = cleaned_name.replace(" ", "_")
            
            # Retrieve or generate ID
            final_app_id = st.session_state.get("temp_app_id")
            if not final_app_id:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                final_app_id = f"LOAN-{cleaned_name}-{timestamp}"
            else:
                # If they updated the name in the form, make sure it reflects the final ID!
                old_dir_str = st.session_state.get("temp_raw_dir")
                timestamp = final_app_id.split("-")[-1]
                new_app_id = f"LOAN-{cleaned_name}-{timestamp}"
                if old_dir_str and Path(old_dir_str).exists() and new_app_id != final_app_id:
                    new_dir = Path("raw_documents") / new_app_id
                    try:
                        Path(old_dir_str).rename(new_dir)
                        st.session_state.temp_raw_dir = str(new_dir)
                        final_app_id = new_app_id
                    except Exception:
                        pass
            
            # Compile documents
            docs_list = []
            if doc_id: docs_list.append("Government-issued Photo ID (Driver's License)")
            if doc_pay: docs_list.append("Last 3 months pay stubs")
            if doc_w2: docs_list.append("W-2 forms (2024, 2025)")
            if doc_bank: docs_list.append("Bank statements (last 3 months)")
            if doc_emp: docs_list.append("Employment verification letter")
            
            # Compile existing loans
            existing_loans = []
            if loan_type != "None" and loan_pay > 0:
                existing_loans.append({
                    "type": loan_type,
                    "remaining_balance": loan_bal,
                    "monthly_payment": loan_pay
                })
            
            # Create JSON payload
            new_app = {
                "application_id": final_app_id,
                "applicant": {
                    "full_name": full_name,
                    "date_of_birth": dob.strftime("%Y-%m-%d"),
                    "ssn_last_four": ssn_last_four or "0000",
                    "email": email or "unknown@email.com",
                    "phone": phone or "555-0000",
                    "address": {
                        "street": street or "N/A",
                        "city": city or "N/A",
                        "state": state or "N/A",
                        "zip": zip_code or "N/A"
                    }
                },
                "employment": {
                    "employer": employer or "N/A",
                    "position": position or "N/A",
                    "years_employed": years_employed,
                    "annual_salary": annual_salary,
                    "employment_type": employment_type
                },
                "financial_profile": {
                    "credit_score": credit_score,
                    "monthly_debt_payments": loan_pay,
                    "monthly_housing_cost": monthly_housing_cost,
                    "checking_account_balance": checking_balance,
                    "savings_account_balance": savings_balance,
                    "existing_loans": existing_loans,
                    "bankruptcies": bankruptcies,
                    "late_payments_last_24_months": late_payments
                },
                "loan_request": {
                    "loan_amount": loan_amount,
                    "loan_purpose": loan_purpose,
                    "requested_term_months": requested_term,
                    "preferred_rate_type": preferred_rate_type
                },
                "documents_submitted": docs_list
            }
            
            # Save to JSON file
            json_path = Path("synthetic_data") / "loan_applications.json"
            try:
                apps = []
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        apps = json.load(f)
                
                if not isinstance(apps, list):
                    apps = []
                
                apps.append(new_app)
                
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(apps, f, indent=2)
                    
                st.session_state.last_created_app_id = final_app_id
                
                # Clear extracted cache
                st.session_state.pop("extracted_data", None)
                st.session_state.pop("temp_app_id", None)
                st.session_state.pop("temp_raw_dir", None)
                
                st.success(f"Successfully created loan application record! ID: {final_app_id}")
                st.rerun()
            except Exception as ex:
                st.error(f"Error saving application: {ex}")

    # Section for triggering background review of the newly created application
    if "last_created_app_id" in st.session_state:
        app_to_run = st.session_state.last_created_app_id
        st.markdown(f"**Ready for Review:** `{app_to_run}`")
        
        if st.button("🚀 Trigger Agent Processing Flow", key="trigger_crew_btn"):
            st.info(f"Triggering background processing for `{app_to_run}`...")
            import subprocess
            import sys
            
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["CREWAI_TRACING_ENABLED"] = "true"
            env["PYTHONPATH"] = "src"
            
            try:
                process = subprocess.Popen(
                    [sys.executable, "src/loan_processing_crew/main.py", app_to_run],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    cwd=os.getcwd(),
                    text=True
                )
                
                with st.spinner("Agents are analyzing application documents and compliance rules..."):
                    stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    st.success("Loan review complete!")
                    st.markdown("You can now select the new ID in the **Trace Inspector & Compliance** tab to review compliance and agent timelines.")
                    # Force data reload by clearing streamlit cache
                    st.rerun()
                else:
                    st.error(f"Agent execution failed with exit code {process.returncode}")
                    st.code(stderr or stdout)
            except Exception as ex:
                st.error(f"Failed to start review process: {ex}")


# =====================================================================
# TAB 4: PHOENIX ARIZE EVALUATION
# =====================================================================
with tab_eval:
    st.markdown("### 🧪 LLM-as-Judge Evaluation — Phoenix Arize")
    st.caption(
        "Run automated evaluations on every loan decision output using GPT-4o-mini as a judge. "
        "Scores are stored in `output/phoenix_evals.db` and displayed below."
    )

    # Phoenix Status Banner
    phoenix_col, link_col = st.columns([4, 1])
    with phoenix_col:
        if PHOENIX_AVAILABLE:
            st.success("✅ Phoenix Arize is installed. Traces are forwarded to Phoenix when the crew runs.")
        else:
            st.error("❌ Phoenix not installed. Run: `uv add arize-phoenix openinference-instrumentation-crewai`")
    with link_col:
        st.link_button("🔍 Open Phoenix UI", "http://localhost:6006", use_container_width=True)

    st.markdown("---")

    # --- Run Evaluations Section ---
    st.markdown("#### ▶️ Run Evaluations")
    run_col1, run_col2, run_col3 = st.columns([3, 2, 2])
    with run_col1:
        output_dir_eval = Path("output")
        decision_files_eval = sorted(output_dir_eval.glob("loan_decision_LOAN-*.md"))
        app_ids_eval = [f.stem.replace("loan_decision_", "") for f in decision_files_eval]
        eval_target = st.selectbox(
            "Application to evaluate",
            ["All Applications"] + app_ids_eval,
            key="eval_target_select",
        )
    with run_col2:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        run_eval_btn = st.button("🚀 Run Evaluation", key="run_eval_btn", use_container_width=True)
    with run_col3:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        clear_eval_btn = st.button("🗑️ Clear All Results", key="clear_eval_btn", use_container_width=True)

    if run_eval_btn:
        target_id = None if eval_target == "All Applications" else eval_target
        with st.spinner(f"Running evaluations on {eval_target}... (calls GPT-4o-mini as judge)"):
            new_results = run_loan_evaluations(application_id=target_id)
        if not new_results.empty:
            st.success(
                f"✅ Evaluated {new_results['application_id'].nunique()} application(s) "
                f"across {len(new_results)} rubric checks."
            )
        else:
            st.warning("No decision files found. Process at least one application first.")
        st.rerun()

    if clear_eval_btn:
        clear_eval_results()
        st.success("Evaluation results cleared.")
        st.rerun()

    st.markdown("---")

    # --- Results Display ---
    eval_df = get_eval_summary()

    if eval_df.empty:
        st.info("No evaluation results yet. Select an application above and click **🚀 Run Evaluation**.")
    else:
        # Summary KPI row
        total_checks = len(eval_df)
        passed = (eval_df["label"] == "PASS").sum()
        failed = (eval_df["label"] == "FAIL").sum()
        avg_score = eval_df["score"].mean()
        unique_apps = eval_df["application_id"].nunique()

        kc1, kc2, kc3, kc4, kc5 = st.columns(5)
        kc1.metric("Applications", unique_apps)
        kc2.metric("Total Checks", total_checks)
        kc3.metric("✅ Pass", int(passed))
        kc4.metric("❌ Fail", int(failed))
        kc5.metric("Avg Score", f"{avg_score:.2f}")

        st.markdown("---")

        # --- Score Heatmap ---
        st.markdown("#### 📊 Score Heatmap — Application × Rubric")
        pivot = eval_df.pivot_table(
            index="application_id", columns="rubric_name", values="score", aggfunc="mean"
        ).round(2)

        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="RdYlGn",
            zmin=0, zmax=1,
            text_auto=True,
            aspect="auto",
            labels={"x": "Evaluation Rubric", "y": "Application ID", "color": "Score"},
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#fafafa" if IS_DARK else "#09090b",
            margin=dict(l=0, r=0, t=30, b=0),
            height=max(300, 70 * len(pivot)),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # --- Pass Rate Bar Chart ---
        st.markdown("#### 📈 Pass Rate by Rubric")
        rubric_summary = (
            eval_df.groupby("rubric_name")
            .apply(lambda g: pd.Series({
                "pass_rate": (g["label"] == "PASS").mean() * 100,
                "avg_score": g["score"].mean(),
                "count": len(g),
            }))
            .reset_index()
        )

        fig_bar = px.bar(
            rubric_summary,
            x="rubric_name",
            y="pass_rate",
            color="avg_score",
            color_continuous_scale="RdYlGn",
            range_color=[0, 1],
            text=rubric_summary["pass_rate"].apply(lambda v: f"{v:.0f}%"),
            labels={"rubric_name": "Rubric", "pass_rate": "Pass Rate (%)", "avg_score": "Avg Score"},
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#fafafa" if IS_DARK else "#09090b",
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
            showlegend=False,
            coloraxis_showscale=False,
        )
        fig_bar.update_traces(textposition="outside")
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- Detailed Results Table ---
        st.markdown("#### 📋 Detailed Evaluation Results")
        app_filter_eval = st.selectbox(
            "Filter by Application",
            ["All"] + sorted(eval_df["application_id"].unique().tolist()),
            key="eval_detail_filter",
        )
        filtered_eval = (
            eval_df if app_filter_eval == "All"
            else eval_df[eval_df["application_id"] == app_filter_eval]
        )

        def _color_label(val):
            if val == "PASS":
                return "background-color: rgba(34,197,94,0.2); color: #22c55e; font-weight:bold"
            elif val == "FAIL":
                return "background-color: rgba(239,68,68,0.2); color: #ef4444; font-weight:bold"
            return ""

        display_eval = filtered_eval[
            ["application_id", "rubric_name", "score", "label", "explanation", "evaluated_at"]
        ].copy()
        display_eval["score"] = display_eval["score"].round(3)

        st.dataframe(
            display_eval.style.map(_color_label, subset=["label"]),
            use_container_width=True,
            hide_index=True,
        )

        # --- Phoenix Deep Link ---
        st.markdown("---")
        st.info(
            "🔍 **Explore traces in Phoenix:** Open [http://localhost:6006](http://localhost:6006) "
            "to inspect agent spans, token usage, and latency waterfall for every processed application. "
            "Phoenix captures traces automatically whenever `uv run loan_processing_crew` is run."
        )

