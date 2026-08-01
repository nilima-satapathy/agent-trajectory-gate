# Agent Trajectory Gate

[![CI](https://github.com/nilima-satapathy/agent-trajectory-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/nilima-satapathy/agent-trajectory-gate/actions/workflows/ci.yml)

**Portfolio Project 7** — AI Test Engineer / GenAI Quality  
**Tagline:** *Tool-calling agents under test · Trajectory scores · Ship gates*

**GitHub:** https://github.com/nilima-satapathy/agent-trajectory-gate  

**Live demo:** https://agent-trajectory-gate.streamlit.app  

Main file: `console/app.py` · Branch: `main`

Planned with [OpenSpec](https://openspec.dev/).

---

## What it does

```text
Engineer defines tools (Python)
        ↓
User question (QA ticket triage)
        ↓
Real LLM plans + calls tools
   — or offline FixtureSUT for CI
        ↓
Trajectory log (tool → args → result → …)
        ↓
Gate scores the path
  L1 trajectory · L2 answer · L3 optional judge
        ↓
PASS / WARN / FAIL + failure taxonomy
        ↓
Trajectory Console (lab UI) · reports/ · Pytest CI
```

**Showcase:** The **path** is the product — not another chatbot score on final text alone.

| Role | Who |
|------|-----|
| Defines tools | **You** (author-defined registry) |
| Calls tools | **Real AI** (tool-calling) |
| Scores the path | **This harness** (L1/L2/L3 + taxonomy) |

The agent does **not** invent tools with AI. See [docs/NOT_CHATBOT.md](docs/NOT_CHATBOT.md).

---

## Quick start

```powershell
cd C:\Users\admin\Code\agent-trajectory-gate
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env

# Offline quality gates (no API key)
pytest tests/ -q -m "not live"
python evals/run_suite.py --suite quick --mode fixture

# Lab UI → http://localhost:8501
python -m streamlit run console/app.py
```

### Live free-tier Groq (optional)

```env
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_...
OPENAI_MODEL=llama-3.1-8b-instant
```

```powershell
python evals/run_suite.py --suite quick --mode live
pytest tests/ -m live -q
```

Live tests are **not** required in CI (no secrets). Use them locally for demos.

---

## Trajectory Console

| Nav | Purpose |
|-----|---------|
| **TRACE** (home) | Run quick/full suite · fixture or live agent · path scores |
| **CATALOG** | Browse/filter golden set · run one case |
| **LIVE** | Single live tool-calling probe |
| **ARCHIVE** | Reports + live dumps |
| **RIG** | Key/mode/judge checklist · free-tier meter |

```powershell
python -m streamlit run console/app.py
```

---

## Not DocQ / QA Sentinel / ChainVerdict

| | Chat / RAG projects | **Agent Trajectory Gate** |
|--|---------------------|---------------------------|
| SUT | Answer or RAG pipeline | **Tool-calling agent loop** |
| Hero UI | Chat | **Trajectory lab console** |
| Artifact | Answer quality | **Tool path + side effects** |

---

## Stack

- Python 3.11+ · Pytest · Streamlit
- OpenAI-compatible client (**Groq**)
- GitHub Actions (offline only)
- Optional L3 judge (off by default)

---

## Docs

| Doc | Content |
|-----|---------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Loop + scoring diagram |
| [docs/INTERVIEW.md](docs/INTERVIEW.md) | 60–90s demo script |
| [docs/NOT_CHATBOT.md](docs/NOT_CHATBOT.md) | Positioning checklist |
| [openspec/changes/init-agent-trajectory-gate/](openspec/changes/init-agent-trajectory-gate/) | Full SDD |

---

## Status

| Phase | Status |
|-------|--------|
| 0–9 Core + live + runner | Done |
| 10 Trajectory Console | **Done** |
| 11 Regression CI | **Done** |
| 12 Docs ship | **Done** |

---

## Interview line

> I built **Agent Trajectory Gate**, a lab that evaluates tool-calling agents by scoring the full tool path — required tools, order, arguments, and side effects — with free-tier Groq live runs, offline fixtures for CI, and a trajectory inspector UI.

---

## License

MIT — portfolio / learning project.
