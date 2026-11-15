# CodeForge — Production-Grade NL-to-Code Multi-Agent System

> Turn plain-English requests into working, tested code — safely, honestly, and affordably.
> Supports **Python functions** and **SQL queries**.

## Architecture

```
User Request
     │
     ▼
┌─────────────────┐     ┌─────────────────┐
│   Guard In      │────▶│  Request Safety  │   R1: PII masking (Luhn, regex)
│   (R1)          │     │  (R2)            │   R2: Block dangerous intent
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   Triage        │────▶│  Escalation     │   R3: Rule-based (not model-based)
│   (R3)          │     │  Check          │   Frustration accumulation across turns
└────────┬────────┘     └────────┬────────┘
         │                       │
    ┌────┴────┐            ┌─────┴──────┐
    │ Escalate│            │  Route     │
    │ P1/P2/P3│            │ Python│SQL │
    │ Ticket  │            └─────┬──────┘
    └─────────┘                  │
                          ┌──────┴──────┐
                    ┌─────┴───┐   ┌─────┴───┐
                    │ Python  │   │  SQL     │
                    │ Pipeline│   │ Pipeline │
                    └─────┬───┘   └─────┬───┘
                          │             │
                    ┌─────┴───┐   ┌─────┴──────┐
                    │ Policy  │   │ validate   │   R2: AST-based (Python)
                    │ Gate    │   │ _sql       │   R7: sqlglot-based (SQL)
                    └─────┬───┘   └─────┬──────┘
                          │             │
                    ┌─────┴───┐   ┌─────┴──────┐
                    │ Sandbox │   │ Role-based │   R2: Separate process, timeout
                    │ Execute │   │ Execute    │   R7: SELECT (+ INSERT/UPDATE for instructors)
                    └─────┬───┘   └────────────┘
                          │
                    ┌─────┴───┐
                    │ Report  │   R2: Built from real pytest exit code
                    └─────────┘
```

## Resilience Stack (R5)

```
Request arrives
  │
  ▼
Tier 1: PRIMARY model (retry with full-jitter backoff, up to 3 attempts)
  │ failed?
  ▼
Tier 2: FALLBACK model (1 retry)
  │ failed?
  ▼
Tier 3: TEMPLATE library (palindrome, factorial, fibonacci, fizzbuzz, list_sum, reverse_string,
        linear/binary search, bubble/selection/insertion/merge/quick sort)
  │ no match?
  ▼
Tier 4: Honest failure — "Service unavailable", never hallucinated code
```

Chaos Mode (toggle in UI) fails 60% of model calls to prove resilience works.

## LLM Calls Per Scenario

| Scenario | LLM Calls | What happens |
|----------|:---------:|-------------|
| Template match (palindrome, factorial, search, sort, etc.) | **0** | Verified code from library |
| Dangerous request (delete files, hack) | **0** | Regex blocks before any LLM |
| PII redaction | **0** | Masked by regex at ingress |
| Role spoof ("I'm an instructor") | **0** | Caught by identity check |
| Escalation (angry / wants human) | **0** | Keyword-based triage |
| Cache hit (same request twice) | **0** | Idempotency key match |
| SQL query (student) | **0** | Denied by role check |
| SQL query (instructor) | **1** | SQL agent only |
| SQL delete/drop request | **0** | Blocked before any LLM, for every role |
| Off-topic question (weather, jokes, news…) | **0** | Polite "coding questions only" reply |
| Normal Python code request | **4** | router → requirements → code_gen → test_gen |

## Team Split

| Member | Ownership | Modules |
|--------|-----------|---------|
| Pipeline Owner | Level 1 agents, LangGraph state, structured outputs | `agents/`, `graph.py`, `state.py`, `models.py` |
| Safety Owner | R1 (identity, PII), R2 (policy, sandbox), R7 (SQL) | `security/`, `execution/`, `sql/` |
| Reliability Owner | R5 (retry, circuit breaker, templates, chaos) | `resilience/` |
| Quality Owner | R3 (escalation), R6 (golden set), demo | `escalation/`, `tests/`, `demo.py` |

## Three Design Decisions We Defend

### 1. Two-layer safety: request intent + code AST
We check the **request text** for dangerous intent (delete files, hack, keylogger) *before* any code is generated. Then we check the **generated code** with `ast` parsing. The LLM can't bypass either layer — both are pure Python functions with unit tests.

### 2. The degraded tier fails closed
When all model tiers are down, template tasks still return code and tests. But the degraded tier **never auto-approves risky code**. An unknown task gets an honest "cannot generate now" — never invented code. Safety over availability.

### 3. Escalation is rule-based, not model-based
The model detects sentiment, but **code makes the escalation decision**. Frustration accumulates across turns and resets on calm turns. Thresholds are unit-tested. A prompt injection can't suppress an escalation.

## Requirements Covered

| # | Requirement | Status | Tests |
|---|-------------|--------|-------|
| Level 1 | Core pipeline (Router → Requirements → CodeGen → TestGen → Orchestrator) | Done | 4 agents + graph |
| R1 | Identity and Privacy (mandatory) | Done | 24 tests |
| R2 | Safe Execution (mandatory) | Done | 33 tests |
| R3 | Escalation and Handoff (chosen) | Done | 15 tests |
| R5 | Resilience (chosen) | Done | 50 tests |
| R6 | Evals as a Gate (mandatory) | Done | 12 golden set + CI |
| R7 | Safe SQL Agent (bonus +10) | Done | 31 tests |
| Bonus | Gradio chat interface (+10) | Done | — |
| **Total** | | | **192 tests** |

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd Sizora-Minds

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Open .env and add your Groq API key:
# GROQ_API_KEY=your-key-here
# Get a free key at: https://console.groq.com/keys

# 5. Run tests (golden set gate — should show 192 passed)
python -m pytest tests/ -v

# 6. Run the demo (all 8 scenarios in terminal)
python demo.py

# 7. Launch the UI
python gradio_app.py
# Opens at http://localhost:7860
```

> **That's it.** Open `http://localhost:7860` in your browser and start using CodeForge.
> Each person runs it on their own machine — no deployment needed.

### UI features

- **Chat** with live "working" feedback, copy buttons, and a downloadable full report per run.
- **User switcher** — identity and role come from config; each user has a separate chat history.
- **Human approval** — code flagged `needs_approval` (e.g. network modules, `open()`) pauses with **Approve & Run** / **Reject** buttons instead of running automatically.
- **Instructor = admin** — instructors can ask "show all student runs" (or name a student, e.g. `student_b`) to see every student's run history with a downloadable report, and can run SQL on every table (see below). Students can only see their own runs and can never gain privileges through chat.

### Roles & permissions

| | Student | Instructor (admin) |
|---|---|---|
| Python code generation + sandbox | ✅ | ✅ |
| View other users' runs | ❌ | ✅ |
| SQL `SELECT` | ❌ | ✅ every table (incl. `users`, PII columns masked) |
| SQL `INSERT` / `UPDATE` | ❌ | ✅ |
| SQL `DELETE` / `DROP` / `TRUNCATE` / `ALTER` | ❌ | ❌ |
| Delete / create files, shell commands, malicious code | ❌ | ❌ |
- **Coding questions only** — off-topic messages (weather, jokes, news, greetings…) get a polite reply asking for a coding question, with no LLM call.
- **Chaos Mode** toggle and one-click **Quick tests** for every scenario (Python, searching, sorting, denied, safety, SQL).

## Event Logging (privacy)

Every pipeline stage writes one JSON line to the `codeforge.events` logger — **only after PII masking**:

```
INFO codeforge.events | {"event": "request_received", "user": "student_a", "request": "my key is [SECRET], write a fizzbuzz function", "pii_masked": true}
INFO codeforge.events | {"event": "template_served", "user": "student_a", "function": "fizzbuzz"}
INFO codeforge.events | {"event": "sandbox_run", "user": "student_a", "tier": "template", "passed": true, "tests_passed": 5, "tests_failed": 0}
```

- The raw message is never logged; `request_received` is emitted only after `mask_pii` runs.
- `log_event` (`app/event_log.py`) masks every string field **again** before writing, so a caller mistake can't leak a secret.
- Provider error messages (which can echo the prompt) are masked before they reach the log or the downloadable report.
- Chat history stores the masked version of what you typed.
- Log level comes from `CODEFORGE_LOG_LEVEL` in `.env` (default `INFO`).

Events: `request_received`, `role_spoof_denied`, `access_denied`, `admin_access_confirmed`, `student_runs_viewed`, `request_denied`, `escalated`, `off_topic_declined`, `sql_denied`, `sql_error`, `sql_executed`, `template_served`, `llm_generated`, `llm_attempt_failed`, `generation_failed`, `code_denied`, `approval_required`, `approval_resolved`, `cache_hit`, `quota_exceeded`, `sandbox_run`.

## LLM Setup Notes

- **TLS behind a corporate proxy:** `app/config.py` uses [`truststore`](https://pypi.org/project/truststore/) so Python verifies certificates with the OS trust store (macOS Keychain / Windows cert store). Verification stays fully on; this only fixes Python 3.14 rejecting proxy CAs that the OS trusts (`CERTIFICATE_VERIFY_FAILED … Basic Constraints of CA cert not marked critical`).
- **Groq free-tier limits:** the free tier allows ~1000 output tokens per minute, so agents cap `max_tokens` (600, or 950 for code generation — see `LLMConfig`). On a 429 the UI waits for the time Groq suggests (max 20 s) and retries.
- **Very large requests** (e.g. a full expression parser) can exceed the output cap; the UI says so and suggests splitting the request.

## Windows Notes

The sandbox runs pytest with a minimal environment so no secrets (like `GROQ_API_KEY`) leak into generated code. On Windows it also passes `SYSTEMROOT`, `SYSTEMDRIVE`, `WINDIR`, `TEMP`, `TMP`, `PATHEXT` and `COMSPEC` — without `SYSTEMROOT`, Winsock can't initialise and pytest plugins that import `asyncio` (e.g. anyio) crash with:

```
OSError: [WinError 10106] The requested service provider could not be loaded or initialized
```

Activate the virtual environment on Windows with `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Project Structure

```
CodeForge/
├── app/
│   ├── config.py              # User identity, LLM config, limits
│   ├── models.py              # All Pydantic models (structured outputs)
│   ├── state.py               # LangGraph TypedDict state
│   ├── graph.py               # LangGraph orchestrator (14 nodes)
│   ├── metering.py            # Token/cost tracking callback
│   ├── event_log.py           # Structured audit log — masks every field before writing
│   ├── agents/                # Level 1: LLM agents
│   │   ├── router.py          # Classifies request type (Python/SQL/unsupported)
│   │   ├── requirements.py    # Extracts function name, params, edge cases
│   │   ├── code_generator.py  # Generates Python code + complexity analysis
│   │   └── test_generator.py  # Generates pytest tests
│   ├── security/              # R1: Identity & Privacy
│   │   ├── privacy.py         # PII masking (Luhn-validated cards, regex)
│   │   ├── identity.py        # Role from config, never from message
│   │   ├── access_control.py  # Per-user run isolation
│   │   └── quota.py           # Per-user rate limiting
│   ├── execution/             # R2: Safe Execution
│   │   ├── policy.py          # Request safety + AST-based code policy
│   │   ├── sandbox.py         # Isolated subprocess execution with timeout
│   │   ├── idempotency.py     # Hash-based dedup (same request runs once)
│   │   └── report.py          # Template-based report from real pytest result
│   ├── escalation/            # R3: Escalation & Handoff
│   │   ├── triage.py          # LLM triage (sentiment, urgency)
│   │   ├── rules.py           # Code-based escalation rules + frustration reset
│   │   └── ticket.py          # P1/P2/P3 ticket creation with SLA
│   ├── resilience/            # R5: Resilience
│   │   ├── retry.py           # Full-jitter backoff (429, 5xx, timeout)
│   │   ├── circuit_breaker.py # Circuit breaker (open after 5 failures)
│   │   ├── templates.py       # 14 sandbox-verified templates (typo-tolerant matching)
│   │   ├── chaos.py           # Chaos switch (60% failure simulation)
│   │   └── fallback.py        # Primary → fallback → template → honest failure
│   └── sql/                   # R7: Safe SQL Agent (bonus)
│       ├── database.py        # Sample SQLite DB (sales, employees, users)
│       ├── validator.py       # sqlglot-based, role-aware validation (no DELETE/DROP ever)
│       └── agent.py           # SQL generation + validation + execution + PII column masking
├── tests/                     # 192 unit + integration tests
│   ├── test_privacy.py        # R1: PII masking (Luhn, regex, negatives)
│   ├── test_policy.py         # R2: Request safety + code policy
│   ├── test_escalation_rules.py  # R3: All escalation rules
│   ├── test_resilience.py     # R5: Chaos, circuit breaker, templates, retry
│   ├── test_sql.py            # R7: 10 attack vectors + legitimate queries
│   ├── test_golden_set.py     # R6: 10 hard (100%) + 12 soft (85%+)
│   ├── test_idempotency.py    # R2: Same request runs once
│   ├── test_identity.py       # R1: Role from config, quota, access control
│   └── test_integration.py    # End-to-end pipeline tests
├── golden_set.json            # R6: 22 evaluation cases
├── demo.py                    # Demo script (8 scenarios)
├── gradio_app.py              # Gradio chat UI
├── .env.example               # Environment template
├── requirements.txt           # Dependencies
└── .github/workflows/ci.yml   # CI gate (pytest on push)
```
