import json
import sqlite3
from datetime import datetime
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
tab_overview, tab_traces = st.tabs(["📊 Executive Summary", "🔍 Trace Inspector & Compliance"])

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
