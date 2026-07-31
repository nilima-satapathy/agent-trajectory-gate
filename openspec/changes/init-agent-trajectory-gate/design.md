## Context

Greenfield **AI Test Engineer** portfolio lab. Prior projects cover RAG products, text eval dashboards, live chat gates, and LangChain RAG evaluation. **Agent Trajectory Gate** fills the agent/tool-calling gap: a real free-tier LLM calls **author-defined** tools; the harness scores the **trajectory**.

## Goals / Non-Goals

**Goals:**

- Author-defined tool registry with schemas and inspectable side effects
- Live agent loop (OpenAI-compatible tool calling) on free-tier Groq
- Fixture agent for offline CI and demos
- L1 trajectory scoring + L2 answer checks + optional L3 judge
- Agent failure taxonomy with human-readable rationales
- Golden suite (≥25 cases) + batch reports
- Free-tier meter for intentional live use
- Professional **Trajectory Console** (lab-first; Live Probe secondary)
- Pytest + GitHub Actions fixture path always green without keys

**Non-Goals:**

- Chat-first Streamlit home like DocQ or QA Sentinel
- AI that invents/creates tools at runtime
- Multi-agent frameworks as MVP
- Production ticketing integrations
- DeepEval/Ragas as primary metrics (trajectory gates are primary; judge optional)
- Pixel-perfect design system beyond Streamlit + CSS tokens

## Decisions

### D1 — Product identity

| Field | Decision |
|-------|----------|
| Name | **Agent Trajectory Gate** |
| Repo | `agent-trajectory-gate` |
| Path | `C:\Users\admin\Code\agent-trajectory-gate` |
| Metaphor | The agent’s **path** is on trial; scoring delivers a **gate** verdict |
| Portfolio slot | Project 7 |

### D2 — Domain SUT story

**QA Ticket Triage Agent** for a fake internal QA org.

User examples:

- “Login fails on Chrome after the last deploy. Create a high-severity bug and assign it to the web team.”
- “Just list open high-severity bugs.” (must **not** create)

Tools are enough to exercise multi-step paths, wrong-tool traps, and state checks—without external APIs.

### D3 — Tools are author-defined (hard rule)

| Rule | Enforcement |
|------|-------------|
| Tools written in Python by engineer | `src/tools/` only registry source |
| Schemas exported to LLM | OpenAI function/tool JSON from registry |
| No runtime tool codegen | Reject any design that asks the model to define new tools in MVP |
| Side effects observable | In-memory store (MVP); optional SQLite |

**MVP tool set:**

| Tool | Kind | Notes |
|------|------|--------|
| `search_known_issues(query)` | read | Optional context step |
| `create_bug(title, severity, description)` | write | Returns `bug_id` |
| `assign_owner(bug_id, team)` | write | Must use real id from create |
| `lookup_user(email)` | read | Optional |
| `list_open_bugs(severity?)` | read | Trap for “list only” cases |

### D4 — Live agent SUT (real AI, free credits)

- Client: OpenAI-compatible Chat Completions with `tools` / tool_calls
- Env: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`
- Default provider docs: **Groq** free tier
  - Quality demo: stronger tool-capable free model (e.g. `llama-3.3-70b-versatile` when available)
  - Cheap smoke: smaller tool-capable free model (e.g. `llama-3.1-8b-instant` when available)
- System prompt: triage agent; must use tools for side effects; never invent bug ids
- Loop: call model → execute tool_calls via registry → append results → repeat until final text or `MAX_TOOL_STEPS` (default 6)
- On 429/rate limit: surface clear error; do not crash console
- Persist each live run trajectory under `reports/live_runs/` for offline re-score

### D5 — Fixture SUT

- `SUT_MODE=fixture` returns pre-authored trajectories + final answers from golden/fixture files
- No network; used by default CI and offline demos
- Fixture paths can deliberately FAIL for taxonomy demos

### D6 — Scoring layers

| Layer | Always? | Cost | Role |
|-------|---------|------|------|
| **L1 Trajectory** | Yes | Free | Required tools, order, args schema/values, step budget, registered tools only, state checks |
| **L2 Answer** | Yes | Free | Must include real ids; must not claim success without tools; forbidden phrases |
| **L3 Judge** | Optional toggle | 1 free-tier call | Rubric quality of bug description / helpfulness |

**Aggregate status:**

- **FAIL** if any critical L1 rule fails OR L2 hard fail OR (L3 on and hard fail)
- **WARN** if soft L1 (extra tools, weak severity mapping) or borderline L2/L3
- **PASS** otherwise

Thresholds and critical vs soft rules live in `config/scoring.yaml`.

### D7 — Failure taxonomy

Primary label per case (single primary + optional secondary):

| Code | Meaning |
|------|---------|
| `OK` | Path + answer acceptable |
| `WRONG_TOOL` | Used tool inappropriate for intent |
| `MISSING_TOOL` | Required tool never called |
| `BAD_ARGS` | Invalid or incomplete arguments |
| `ORDER_ERROR` | Tools out of required order |
| `HALLUCINATED_TOOL` | Tool name not in registry |
| `INFINITE_LOOP` | Hit max steps / repeated identical calls |
| `STATE_MISMATCH` | Tool “ok” but store wrong |
| `ANSWER_LIE` | Final text claims actions not performed |
| `MODEL_ERROR` | API/parse/transport failure |

Classifier is deterministic from scores + trajectory (unit-testable, no network).

### D8 — UI/UX (lab console first)

**Product principle:** *The path is the product.*

**Information architecture:**

```text
Suite Run      ← HOME
Cases
Trajectory     ← detail deep-link
Live Probe     ← secondary (single-case real AI)
Reports
Setup
```

**Not home:** multi-turn chat transcript as sole hero (rejected Option C).

**Design system tokens:**

| Token | Value |
|-------|--------|
| Light bg | `#F7F6F3` warm paper |
| Dark bg | `#0F1419` |
| Accent | Teal `#0D9488` |
| PASS | `#16A34A` |
| WARN | `#D97706` |
| FAIL | `#DC2626` |
| Tool step | Indigo `#4F46E5` |
| Radius | 10–12px cards; pill chips |
| Type | System UI sans + mono for JSON/args |

**Key screens:**

1. **Suite Run** — KPI cards (cases / PASS / WARN / FAIL), Run quick|full, results table, taxonomy summary, mode badge (Fixture|Live), free-tier meter when live
2. **Trajectory Detail** — input, expected constraints, **vertical tool timeline**, score card (L1/L2/L3), side-effect store snapshot, raw JSON copy
3. **Live Probe** — single user message + presets → live step list → verdict (secondary nav)
4. **Setup** — key presence, model, mode, max steps, judge toggle, checklist

**Streamlit structure:**

- `console/app.py` entry + nav
- Pages under `console/pages/`
- Shared CSS for chips/timeline
- Explicit **Run** buttons (no accidental re-runs on widget interaction)

### D9 — Free-tier strategy

- Judge **OFF** by default
- `MAX_TOOL_STEPS=6`
- Meter tracks chat/tool-loop and judge calls for this app
- Prefer fixture for full suite in CI; live smoke 5–10 cases locally
- Cache live trajectories to re-score without re-calling the model

### D10 — Golden suite

- Location: `golden/cases/` or `golden/agent_cases.json`
- Schema fields: `id`, `input`, `expected` (must_call_tools, order_constraints, arg constraints, answer_must_include), `tags`, `case_type`, optional `fixture_trajectory`
- Mix: happy path, list-only, order traps, adversarial invent-id, multi-step, edge, regression locks
- Suites: `quick` (≥8), `full` (≥25)

### D11 — Package layout

```text
agent-trajectory-gate/
  openspec/
  src/
    config/
    tools/
    agent/          # loop, prompts
    llm/            # openai-compatible client, fixture
    scoring/        # L1, L2, taxonomy
    judge/          # optional L3
  golden/
  config/           # scoring.yaml
  evals/            # run_suite.py
  console/          # Streamlit
  tests/
  reports/
  docs/
  scripts/
```

### D12 — Testing strategy

| Layer | What | Network |
|-------|------|---------|
| Unit | Registry, L1/L2, taxonomy pure functions | No |
| Integration | Fixture suite end-to-end scoring | No |
| Live smoke | `@pytest.mark.live` few cases | Yes (key) |
| Manual | Console demo script | Optional |

## Architecture

```text
                    ┌─────────────────────┐
                    │ Golden cases JSON   │
                    └──────────┬──────────┘
                               ▼
┌──────────────┐     complete(case)      ┌──────────────────────────┐
│ Suite runner │ ──────────────────────► │ SUT: live agent | fixture│
└──────────────┘                         └────────────┬─────────────┘
                                                      │ trajectory + answer
                                                      ▼
                                             ┌────────────────┐
                                             │ L1 path score  │
                                             │ L2 answer      │
                                             │ L3 judge (opt) │
                                             └────────┬───────┘
                                                      ▼
                                             taxonomy + verdict
                                                      │
                     ┌────────────────────────────────┼────────────────────┐
                     ▼                                ▼                    ▼
              reports/*.json                 Trajectory Console      Pytest / CI
```

**Agent loop (live):**

```text
messages = [system, user]
for step in 1..max_steps:
  resp = llm.chat(messages, tools=registry.schemas)
  if resp.tool_calls:
    for call in resp.tool_calls:
      result = registry.execute(call.name, call.args)
      append tool message; log step
  else:
    return final_text, trajectory
return forced stop (INFINITE_LOOP if unfinished)
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Free model weak at tool calling | Fixture demos; document model choice; softer WARN band; prefer stronger free model for live demo |
| Rate limits | Meter, clear errors, fixture fallback messaging |
| Scope creep (multi-agent, real Jira) | Non-goals; phase gates |
| Looks like chatbot | Suite Run is home; NOT_CHATBOT.md; Live Probe secondary |
| Flaky live CI | Live never required in default GHA |

## Stretch (post-MVP)

1. SQLite run history + trend chart
2. Side-by-side two-model trajectory compare
3. Export HTML audit report for interviews
4. Repair loop: one re-prompt on FAIL then re-score
5. Promptfoo cross-link for security cases (future project family)

## UI design reference (Option A + secondary Live Probe)

Approved IA: **Lab console first** with Live Probe as secondary page. Chat-first home is rejected.
