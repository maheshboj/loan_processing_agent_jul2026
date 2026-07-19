# 🎓 Improved Prompts — Loan Processing Agentic AI Project
> **Purpose:** Rebuild this project from scratch efficiently for teaching students Agentic AI.  
> **Stack:** CrewAI · Python · Streamlit · OpenTelemetry · LiteLLM · GitHub Actions

---

## 🔴 What Went Wrong in the Original Build (Lessons Learned)

| # | Problem | Root Cause | Impact |
|---|---------|-----------|--------|
| 1 | `NameError: name 'os' is not defined` | Import not included when code was auto-generated | Runtime crash, needed a fix prompt |
| 2 | `StreamlitValueBelowMinError: value 0.0 < min_value 500.0` | LLM extraction returned `0` for missing fields; no clamping guard | Repeated crashes, needed 2 fix prompts |
| 3 | `invalid pdf header: b'<!--\n'` | PDFs were generated as Markdown and renamed `.pdf` — not real binary PDFs | `pypdf` couldn't read them; extraction returned empty/zero data |
| 4 | `ModuleNotFoundError: No module named 'litellm'` | Dependency added to code but not installed via `uv add` | Server startup failure |
| 5 | Document upload was an afterthought | Original Streamlit prompt described a manual form, upload added later | Required rework of the form logic |
| 6 | Stale Streamlit session state persisted bad data | Hot-reload didn't clear `st.session_state`; old `loan_amount=0` stayed | Needed server restart + session sanitizer |
| 7 | Multiple vague "proceed" confirmations | Implementation plans split into too many approval gates | Slowed down the build |

---

## ✅ IMPROVED PROMPTS — Use These When Rebuilding

---

### PHASE 1 — Core CrewAI Project

#### Prompt 1.1 — Full Project Scaffold
```
Build me a complete, end-to-end personal loan processing multi-agent system using CrewAI and Python.

Requirements:
- Use `uv` for dependency management (pyproject.toml)
- Agents: Document Verifier, Underwriter, Risk Analyst, Compliance Officer, Final Decision Maker
- Tools: document_check_tool, underwriting_tool, fraud_detection_tool, compliance_tool
- Each agent should have a clearly defined role, goal, and backstory in agents.yaml
- Tasks should be defined in tasks.yaml with expected_output for each
- Entry point: src/loan_processing_crew/main.py with a run() function that loops over all applications
- Output: Write individual loan decision reports to output/loan_decision_<LOAN_ID>.md
- Include proper error handling and logging throughout
- Make sure all Python imports (os, json, pathlib, datetime, etc.) are explicitly included at the top of every file
```

#### Prompt 1.2 — Synthetic Test Data (All-in-One)
```
Create a synthetic test dataset for the loan processing system covering ALL of these 9 scenarios:
1. Normal approval (good credit, stable income)
2. Boundary case (credit score exactly at threshold)
3. High-risk (high DTI ratio)
4. Fraudulent signals (income/document inconsistency)
5. Incomplete application (missing documents)
6. Escalation required (manual review needed)
7. Rejection (poor credit history)
8. Self-employed applicant
9. Edge case (very high loan amount)

Save as synthetic_data/loan_applications.json with this exact structure per record:
{
  "application_id": "LOAN-2026-XXXXX",
  "applicant": { full_name, date_of_birth, ssn_last_four, email, phone, address{} },
  "employment": { employer, position, years_employed, annual_salary, employment_type },
  "financial_profile": { credit_score, monthly_debt_payments, monthly_housing_cost,
                         checking_account_balance, savings_account_balance,
                         existing_loans[{type, remaining_balance, monthly_payment}],
                         bankruptcies, late_payments_last_24_months },
  "loan_request": { loan_amount, loan_purpose, requested_term_months, preferred_rate_type },
  "documents_submitted": [],
  "status": "pending",
  "risk_flags": []
}
```

#### Prompt 1.3 — Real PDF Documents (Critical Fix)
```
Generate realistic supporting PDF documents for each of the 9 loan applications.
IMPORTANT: These must be genuine binary PDF files (not Markdown renamed to .pdf).
Use Python's `fpdf2` library (add it to pyproject.toml) to programmatically create PDFs.

For each applicant, generate these document types:
- driver_license.pdf (name, DOB, address)
- employment_letter.pdf (employer, position, salary, start date)
- paystub_Jan.pdf, paystub_Feb.pdf, paystub_Mar.pdf (monthly gross/net pay)
- bank_statement.pdf (account balances, recent transactions)
- w2_2024.pdf, w2_2025.pdf (annual wages and tax withheld)

Save all documents under: raw_documents/<application_id>/
Write a generate_pdfs.py script that creates all documents when run.
```

#### Prompt 1.4 — Consolidated Report + Pytest + CI/CD (Combined)
```
Do the following three things:

1. CONSOLIDATED REPORT: Modify main.py so that after processing all applications, it writes a
   single consolidated report to output/loan_decisions_consolidated.md containing a summary
   table (Application ID | Applicant | Decision | Risk Score | Key Flags) followed by
   individual decision sections for each application.

2. PYTEST SUITE: Create tests/test_loan_processing.py with 9 pytest test functions,
   one per scenario in loan_applications.json. Each test should:
   - Run the crew on a single application
   - Assert the output file was created
   - Assert the decision contains expected keywords (e.g. "APPROVED", "REJECTED", "ESCALATE")
   - Assert no Python exceptions were raised

3. GITHUB ACTIONS CI/CD: Create .github/workflows/ci.yml that:
   - Triggers on push and pull_request to main
   - Sets up Python 3.11 and installs uv
   - Runs `uv sync` to install dependencies
   - Runs `uv run pytest tests/ -v --tb=short`
   - Uploads test results as artifacts
   - Requires OPENAI_API_KEY as a GitHub secret
```

---

### PHASE 2 — OpenTelemetry Observability Dashboard (All-in-One)

#### Prompt 2.1 — Telemetry + Dashboard (Combined)
```
Build a complete observability system for the loan processing crew with two parts:

PART A — Telemetry (src/loan_processing_crew/telemetry.py):
- Hook into CrewAI's event bus (crewai_event_bus) to capture: task start/end, tool calls,
  LLM completions, agent handoffs, and errors
- Use OpenTelemetry semantic conventions for span attributes:
  gen_ai.system, gen_ai.request.model, gen_ai.usage.input_tokens, gen_ai.usage.output_tokens
- Implement a custom SQLiteSpanExporter that writes spans to output/telemetry.db
- Schema: spans table (trace_id, span_id, parent_span_id, name, start_time, end_time,
  duration_ms, attributes JSON, status, loan_application_id)
- Schema: compliance_audit table (event_time, application_id, agent_name, action, outcome, notes)
- Track the active loan_application_id using a thread-safe global so all spans are linked to it
- Include all required imports (os, json, sqlite3, threading, datetime, etc.)

PART B — Streamlit Dashboard (src/loan_processing_crew/dashboard.py):
- Add streamlit, plotly, pandas to pyproject.toml before writing the dashboard
- Three tabs:

  TAB 1 - Executive Summary:
  * KPI cards: total applications, avg token cost, avg latency, error rate
  * Bar chart: token usage per application
  * Line chart: task latency trends
  * Pie chart: decision distribution (Approved/Rejected/Escalated)

  TAB 2 - Trace Inspector & Compliance:
  * Dropdown to select any loan_application_id
  * Gantt chart (Plotly) showing task timeline for selected application
  * Compliance checklist (did each required agent run? were all docs verified?)
  * Raw span attribute tree (expandable JSON per span)

  TAB 3 - New Application Form (Document Upload):
  * File uploader accepting multiple PDF, TXT, and JSON files (allow_multiple=True)
  * On upload: save files to raw_documents/LOAN-TEMP-<timestamp>/
  * Use pypdf (add to pyproject.toml) to extract text from PDFs
  * Use litellm (add to pyproject.toml with `uv add litellm`) to call gpt-4o with the
    extracted text and return structured JSON matching the loan_applications.json schema
  * IMPORTANT: After LLM extraction, clamp ALL numeric fields to their valid ranges before
    displaying in form widgets:
    - loan_amount: minimum 500.0 (default 50000.0 if missing/zero)
    - credit_score: clamp between 300 and 850 (default 750)
    - requested_term_months: clamp between 6 and 120 (default 36)
    - annual_salary, balances, housing_cost: minimum 0.0
  * Rename folder from LOAN-TEMP to LOAN-<CLEANNAME>-<TIMESTAMP> using extracted applicant name
  * Pre-populate form fields with extracted values; user can edit any field
  * Submit button appends the record to synthetic_data/loan_applications.json
  * "Trigger Agent Processing" button spawns a background subprocess running main.py
    with env vars: PYTHONPATH=src, PYTHONIOENCODING=utf-8, CREWAI_TRACING_ENABLED=true

- Use a dark/light theme toggle
- Use Plotly for all charts
- Run with: uv run streamlit run src/loan_processing_crew/dashboard.py
```

---

### PHASE 3 — Git & Documentation

#### Prompt 3.1 — Git Setup (Clean)
```
Help me set up git for this project:
1. Initialize git if not already done
2. Create a .gitignore that excludes: .venv/, __pycache__/, .env, output/*.db,
   output/*.md, raw_documents/, *.pyc, .pytest_cache/, uv.lock (optional)
3. Create a comprehensive README.md with:
   - Project overview with architecture diagram (Mermaid)
   - Prerequisites (Python 3.11+, uv, OpenAI API key)
   - Setup instructions (clone, uv sync, .env setup)
   - How to run: crew processing, Streamlit dashboard, pytest
   - Folder structure explanation
   - How the observability system works
4. Stage all files, commit with message "feat: complete loan processing agentic AI system"
5. Show me the commands to push to a new GitHub remote repository
```

---

## 📐 Key Design Principles to Specify Upfront

When prompting from scratch, always state these explicitly to avoid bugs:

### ✅ Always Say:
- `"Include all Python standard library imports (os, json, sys, datetime, pathlib, threading) explicitly at the top of every file"`
- `"After extracting data from LLM, clamp all numeric values to their valid min/max ranges before passing to Streamlit widgets"`
- `"Generate real binary PDF files using fpdf2, not markdown files renamed to .pdf"`
- `"Add all new libraries to pyproject.toml AND run uv add <package> before writing code that imports them"`
- `"Clear st.session_state when starting a new extraction run to avoid stale data conflicts"`
- `"Combine implementation + proceed into a single prompt wherever possible to reduce back-and-forth"`

### 🎯 Prompt Structure Template for Students:
```
CONTEXT: [What the system does]
TECH STACK: [Languages, frameworks, libraries with versions]
REQUIREMENTS:
  - [Functional requirement 1]
  - [Functional requirement 2]
CONSTRAINTS:
  - [Import guard, clamping guard, etc.]
OUTPUT FORMAT: [File paths, schema, structure]
```

---

## 🔄 Recommended Rebuild Order (6 Prompts Total)

| Step | Prompt | What It Produces |
|------|--------|-----------------|
| 1 | Prompt 1.1 | Full CrewAI scaffold, agents, tools, main.py |
| 2 | Prompt 1.2 | loan_applications.json with 9 test scenarios |
| 3 | Prompt 1.3 | Real PDF documents via fpdf2 |
| 4 | Prompt 1.4 | Consolidated report + pytest + CI/CD workflow |
| 5 | Prompt 2.1 | telemetry.py + full Streamlit dashboard with upload |
| 6 | Prompt 3.1 | Git, README, push to GitHub |

**Total: 6 prompts vs 18 original → 67% reduction in iterations**

---

## 💡 Teaching Tips

1. **Show the architecture first** — Draw the agent graph on a whiteboard before writing any code
2. **Use Prompt 1.3 early** — Real PDFs are critical for the extraction pipeline; students often skip this
3. **Demo the clamping bug live** — It's a great teaching moment about LLM output validation
4. **Commit after each phase** — Use git tags (`v1-crew`, `v2-dashboard`) so you can reset and replay
5. **Show the OTel traces live** — The Gantt chart in Tab 2 is the most visually impressive part for students
6. **Have a backup `.env`** — Keep a pre-filled `.env` with a valid `OPENAI_API_KEY` ready for live demos
