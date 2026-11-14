# CodeForge — Production-Grade NL-to-Code Multi-Agent System

> Turn plain-English requests into working, tested Python code — safely, honestly, and affordably.

## Architecture Flowchart

```
                        ┌──────────────┐
                        │   User       │
                        │   Request    │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │   Guard In   │ ← R1: Mask PII, load identity from
                        │  (R1: PII    │   config, check quota
                        │   masking)   │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │   Triage     │ ← R3: Sentiment, urgency, wants_human
                        │  (R3: LLM)   │   (single LLM call)
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │  Escalation  │ ← R3: Code-based rules decide
                        │   Check      │   (not the model)
                        └──────┬───────┘
                          ╱         ╲
                    escalate     no escalation
                       │              │
                ┌──────▼──────┐  ┌───▼────────┐
                │ Create P1   │  │   Router    │ ← Level 1: Structured output
                │ Ticket      │  │  (Parser)   │
                │ + Handoff   │  └───┬────────┘
                └─────────────┘      │
                                ┌────▼─────────┐
                                │ Requirements │ ← Level 1: Extract function
                                │   Agent      │   name, params, edge cases
                                └────┬─────────┘
                                     │
                                ┌────▼─────────┐
                                │  Code Gen    │ ← Level 1 + R5: Primary model
                                │  Agent       │   → fallback → template tier
                                └────┬─────────┘
                                     │
                                ┌────▼─────────┐
                                │  Test Gen    │ ← Level 1 + R5: Same fallback
                                │  Agent       │   cascade
                                └────┬─────────┘
                                     │
                           ┌─────────▼──────────┐
                           │   Policy Gate      │ ← R2: Pure function on AST
                           │ evaluate_code_     │   (never executes code)
                           │ policy(code)       │
                           └─────────┬──────────┘
                            ╱        │        ╲
                        DENY    NEEDS_APPROVAL  ALLOW
                         │           │            │
                    ┌────▼──┐   ┌───▼────────┐  ┌▼──────────┐
                    │Refuse │   │  Human     │  │  Sandbox  │ ← R2: Separate process,
                    │& Log  │   │  Approval  │  │ Execution │   temp dir, timeout
                    └───────┘   │ (interrupt)│  └─────┬─────┘
                                └───┬────────┘        │
                                approve/reject    ┌───▼────────┐
                                    │             │  Report    │ ← R2: Template from
                                    └─────────────│ (pytest    │   real exit code
                                                  │  result)   │
                                                  └────────────┘
```

## Team Split

| Member | Ownership | Modules |
|--------|-----------|---------|
| Pipeline Owner | Level 1 agents, LangGraph state, structured outputs | `agents/`, `graph.py`, `state.py`, `models.py` |
| Safety Owner | R1 (identity, PII), R2 (policy, sandbox) | `security/`, `execution/` |
| Reliability Owner | R5 (retry, circuit breaker, templates, chaos) | `resilience/` |
| Quality Owner | R3 (escalation), R6 (golden set), demo | `escalation/`, `tests/`, `demo.py` |

## Three Design Decisions We Defend

### 1. Policy gate is a pure function on AST, not an LLM call
`evaluate_code_policy(code)` parses with `ast`, walks the tree, and returns `allow`/`needs_approval`/`deny`. It is deterministic, zero-cost, infinitely fast, and cannot be prompt-injected. An LLM-based policy could be convinced to allow dangerous code; ours cannot.

### 2. The degraded tier fails closed
When all model tiers are down, template tasks still return code and tests. But the degraded tier **never auto-approves risky code** (any `needs_approval` verdict becomes a denial). An unknown task gets an honest "cannot generate now" plus a support ticket — never invented code. We chose safety over availability.

### 3. Escalation is rule-based, not model-based
The model detects sentiment (one LLM call for triage), but **code makes the escalation decision**. Thresholds are unit-tested pure Python: `frustration_score >= 1.0`, `policy_denials >= 2`, `wants_human == True`. This means we can guarantee escalation behavior in CI, and a prompt injection can't suppress an escalation.

## Requirements Covered

| # | Requirement | Status |
|---|-------------|--------|
| Level 1 | Core pipeline (Router → Requirements → CodeGen → TestGen → Orchestrator) | Done |
| R1 | Identity and Privacy (mandatory) | Done |
| R2 | Safe Execution (mandatory) | Done |
| R3 | Escalation and Handoff (chosen) | Done |
| R5 | Resilience (chosen) | Done |
| R6 | Evals as a Gate (mandatory) | Done |
| Bonus | Gradio chat interface (+10) | Done |

## Quick Start

## Quick Start

### 1. Create Virtual Environment

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt)**
```cmd
py -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Set Up Environment

**macOS / Linux**
```bash
cp .env.example .env
```

**Windows (PowerShell)**
```powershell
Copy-Item .env.example .env
```

**Windows (Command Prompt)**
```cmd
copy .env.example .env
```

Edit `.env` and add your API key.

### 4. Run Tests (Golden Set Gate)

```bash
python -m pytest tests/ -v
```

### 5. Run Demo

```bash
python demo.py
```

### 6. Launch Gradio Interface

```bash
python gradio_app.py
```

**Note:** Make sure your virtual environment is activated before installing dependencies or running the application. Each developer should create their own `.venv` locally.

One small Windows issue: If PowerShell blocks virtual environment activation due to execution policy, run:


Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

## Project Structure

```
CodeForge/
├── app/
│   ├── config.py              # User identity, LLM config, limits
│   ├── models.py              # All Pydantic models (structured outputs)
│   ├── state.py               # LangGraph TypedDict state
│   ├── graph.py               # LangGraph orchestrator
│   ├── agents/                # Level 1 agents
│   │   ├── router.py          # Classifies request type
│   │   ├── requirements.py    # Extracts structured requirements
│   │   ├── code_generator.py  # Generates Python code
│   │   └── test_generator.py  # Generates pytest tests
│   ├── security/              # R1: Identity & Privacy
│   │   ├── privacy.py         # PII masking (regex-based)
│   │   ├── identity.py        # Role from config
│   │   ├── access_control.py  # Per-user run isolation
│   │   └── quota.py           # Per-user rate limiting
│   ├── execution/             # R2: Safe Execution
│   │   ├── policy.py          # AST-based policy gate
│   │   ├── sandbox.py         # Isolated subprocess execution
│   │   ├── idempotency.py     # Hash-based dedup
│   │   └── report.py          # Template-based report builder
│   ├── escalation/            # R3: Escalation & Handoff
│   │   ├── triage.py          # LLM triage (sentiment, urgency)
│   │   ├── rules.py           # Code-based escalation rules
│   │   └── ticket.py          # Ticket creation with SLA
│   └── resilience/            # R5: Resilience
│       ├── retry.py           # Full-jitter backoff
│       ├── circuit_breaker.py # Circuit breaker pattern
│       ├── templates.py       # Deterministic template library
│       ├── chaos.py           # Chaos switch (60% failure)
│       └── fallback.py        # Model cascade + template fallback
├── tests/                     # All unit tests
├── golden_set.json            # R6: 22 evaluation cases
├── demo.py                    # Demo script for all scenarios
├── gradio_app.py              # Gradio chat interface (+10)
└── .github/workflows/ci.yml   # CI gate
```
