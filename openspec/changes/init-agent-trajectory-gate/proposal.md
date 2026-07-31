## Why

Portfolio Projects 1–6 prove API/UI automation, building a **RAG chat product (DocQ)**, batch eval for a testing assistant, a **live gated chatbot (QA Sentinel)**, and a **LangChain RAG quality lab (ChainVerdict)**.

Hiring managers for **AI Test Engineer / GenAI QA** roles still ask:

1. *“How do you test **agents** that call tools — not just chat answers?”*
2. *“How do you score the **path** (tool order, args, side effects), not only the final text?”*
3. *“Can you run that against a **real** free-tier model and still keep **offline CI**?”*

Those gaps are not filled by:

| Prior project | Gap for agent QA |
|---------------|------------------|
| DocQ | Product RAG chat; no tool-calling trajectory |
| LLM Eval Dashboard | Text golden/red-team; no multi-step tools |
| QA Sentinel | Answer-level gate on chat; not tool path |
| ChainVerdict | RAG retrieve→generate; not agent tool loop |

**Agent Trajectory Gate** is a greenfield **quality lab** for tool-calling agents. The agent loop is the **system under test (SUT)**. Predefined tools are the **action surface**. Trajectory scoring is the **release gate**. The UI is a **Trajectory Console** (suites, timelines, taxonomy)—not “chat with the bot” as the home experience.

### Explicit differentiation

| | **QA Sentinel (P5)** | **ChainVerdict (P6)** | **Agent Trajectory Gate (P7)** |
|--|---------------------|------------------------|--------------------------------|
| Hero surface | Chat + answer gate | RAG eval console | **Trajectory lab console** |
| SUT | Chat completion | LangChain RAG | **Tool-calling agent loop** |
| Primary artifact | Answer + PASS/WARN/FAIL | Metrics + retrieval taxonomy | **Trajectory JSON + tool timeline** |
| Failure classes | Policy / golden / judge | RETRIEVAL / GENERATION | `WRONG_TOOL`, `BAD_ARGS`, `ORDER_ERROR`, … |
| Real AI role | Generate answer (+ optional judge) | Generate grounded answer | **Plan + call tools** (Groq free tier) |
| Tools | N/A | N/A | **Author-defined** (never model-created in MVP) |

If a reviewer can describe this repo as “another chatbot with scores,” the proposal has failed.

### Core product truth

```text
Engineer defines tools  →  Real LLM calls tools  →  Harness scores the path
```

The agent does **not** invent tools with AI. It **uses** a fixed toolkit correctly (or fails the gate).

## What Changes

Greenfield product **Agent Trajectory Gate** (`agent-trajectory-gate`):

- **Tool registry** — Python tools + JSON schemas + in-memory (or SQLite) side effects for a QA Ticket Triage domain
- **Agent SUT (live)** — multi-step tool-calling loop via OpenAI-compatible API (default: Groq free tier)
- **Fixture SUT** — offline deterministic trajectories for CI and demos without keys
- **Trajectory scoring (L1)** — required tools, order constraints, arg validity, step budget, no hallucinated tools
- **Answer checks (L2)** — final text consistent with tool results (e.g. must cite real `bug_id`)
- **Optional judge (L3)** — free-tier LLM rubric; **off by default** to save credits
- **Failure taxonomy** — agent-specific root-cause labels
- **Eval suite** — golden cases (≥25; quick seed ≥8) + batch runner + `reports/`
- **Free-tier meter** — request/token visibility for live demos
- **Trajectory Console** — Streamlit lab UI: Suite Run home, Cases, Trajectory Detail timeline, Live Probe (secondary), Reports, Setup
- **Regression CI** — Pytest fixture suite always; `@pytest.mark.live` opt-in
- OpenSpec SDD artifacts, README, interview script

## Project naming

| Field | Value |
|-------|--------|
| **Display name** | **Agent Trajectory Gate** |
| **Repo / path** | `agent-trajectory-gate` → `C:\Users\admin\Code\agent-trajectory-gate` |
| **GitHub (later)** | `nilima-satapathy/agent-trajectory-gate` |
| **Tagline** | *Tool-calling agents under test · Trajectory scores · Ship gates* |
| **Why this name** | **Agent** = SUT class; **Trajectory** = what we measure; **Gate** = PASS/WARN/FAIL ship decision |

### Name alternatives considered

| Name | Why not primary |
|------|-----------------|
| PathVerdict | Strong sibling to ChainVerdict; user preferred domain-clearer name |
| ToolTrail | Friendly; weaker CI/gate signal |
| TrajectoryGate | Close; user chose full **Agent Trajectory Gate** |
| AgentGate | Shorter; less specific about path scoring |

## Capabilities

### New Capabilities

- `tool-registry`: Author-defined tools, schemas, and side-effect store
- `agent-sut`: Live multi-step tool-calling agent against OpenAI-compatible LLM
- `fixture-sut`: Offline deterministic agent trajectories for CI/demo
- `trajectory-scoring`: L1 deterministic path gates on recorded trajectories
- `failure-taxonomy`: Map score outcomes to agent failure classes
- `answer-checks`: L2 final-answer consistency with tool results
- `optional-judge`: L3 free-tier LLM-as-judge (opt-in)
- `eval-suite`: Golden cases, batch runner, reports
- `free-tier-meter`: Live usage visibility for free cloud credits
- `trajectory-console`: Lab UI (path inspector; not chat-home)
- `regression-ci`: Pytest + GitHub Actions gates

### Modified Capabilities

- (none — greenfield; no prior `openspec/specs/` source of truth)

## Impact

- New portfolio repo demonstrating **agent QA** with real free-tier tool-calling
- Complements P3–P6 without overlapping primary SUT type
- UI/UX designed as a professional lab console with secondary Live Probe
- CI remains green without API keys; live demos intentional via meter

## Non-goals (MVP)

- Multi-agent swarms / CrewAI-style orchestration
- Model-generated tool code at runtime
- Real Jira/GitHub production write APIs (mock tools only)
- Full RAG pipeline (one optional `search_known_issues` tool is enough)
- Promptfoo-scale red-team plugin library (separate future project)
- Multi-tenant auth, SSO, production SLAs
- Paid OpenAI as default provider
