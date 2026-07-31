## Phase overview

Implement in order. Each section is independently verifiable. Prefer offline checks first; live Groq only when phase requires it.

| Section | Phase id | Outcome |
|---------|----------|---------|
| 0 | `0-identity` | Name lock, README, NOT_CHATBOT, OpenSpec |
| 1 | `1-scaffold` | Package layout, deps, settings, markers |
| 2 | `2-tool-registry` | Tools + store + schemas |
| 3 | `3-fixture-sut` | Offline trajectories |
| 4 | `4-trajectory-scoring` | L1 + unit tests |
| 5 | `5-failure-taxonomy` | Classifier + tests |
| 6 | `6-golden-suite` | ≥25 cases; quick ≥8 |
| 7 | `7-agent-sut-live` | Groq tool-calling loop |
| 8 | `8-optional-judge` | L3 opt-in |
| 9 | `9-eval-runner` | Batch suite + reports |
| 10 | `10-trajectory-console` | Streamlit lab UI |
| 11 | `11-regression-ci` | GHA fixture CI |
| 12 | `12-docs-ship` | Interview + demo docs |

```powershell
# When phase-gate harness exists:
# python scripts/run_phase_gate.py --phase <id>
```

---

## 0. Identity lock (before app code)

- [x] 0.1 Confirm name **Agent Trajectory Gate** / repo `agent-trajectory-gate` (reject chat-bot naming)
- [x] 0.2 Write root `README.md` skeleton: tagline, differentiation table, architecture
- [x] 0.3 Add `docs/NOT_CHATBOT.md` (positioning checklist)
- [x] 0.4 Land `openspec/config.yaml` + this change folder (proposal, design, tasks, capability specs)

## 1. Scaffold

- [x] 1.1 Create package layout: `src/config/`, `src/tools/`, `src/agent/`, `src/llm/`, `src/scoring/`, `src/judge/`, `golden/`, `config/`, `evals/`, `console/`, `tests/`, `reports/`, `docs/`, `scripts/`
- [x] 1.2 `requirements.txt` + `requirements-dev.txt` (openai-compatible client, pytest, streamlit, python-dotenv, pyyaml)
- [x] 1.3 `.env.example` (Groq/OpenAI-compatible, `SUT_MODE`, `JUDGE_ENABLED`, `MAX_TOOL_STEPS`)
- [x] 1.4 `.gitignore`, `pytest.ini` with `live` marker
- [x] 1.5 `src/config/settings.py` loading env + paths


## 2. Tool registry

- [x] 2.1 Implement in-memory bug/user/KB store
- [x] 2.2 Implement tools: `search_known_issues`, `create_bug`, `assign_owner`, `lookup_user`, `list_open_bugs`
- [x] 2.3 Export OpenAI-compatible tool schemas from registry
- [x] 2.4 `registry.execute(name, args)` with validation errors as structured tool results
- [x] 2.5 Unit tests: create→assign side effects; unknown tool rejected


## 3. Fixture SUT

- [x] 3.1 `FixtureSUT.run(case)` returns trajectory + final_answer from case/fixture data
- [x] 3.2 Support deliberate FAIL fixtures for taxonomy demos
- [x] 3.3 No network imports required on fixture path


## 4. Trajectory scoring (L1) + answer checks (L2)

- [x] 4.1 L1: required tools, order constraints, arg constraints, max steps, registered-only tools
- [x] 4.2 L1: optional state checks against store snapshot
- [x] 4.3 L2: answer_must_include, no answer-lie (claims create without tool), forbidden phrases
- [x] 4.4 Aggregate PASS/WARN/FAIL from critical vs soft rules (`config/scoring.yaml`)
- [x] 4.5 Unit tests covering each critical failure mode (no network)


## 5. Failure taxonomy

- [x] 5.1 `classify_failure(scores, trajectory, case) -> label + rationale`
- [x] 5.2 Unit tests for each taxonomy code
- [x] 5.3 Attach taxonomy to case results in reports


## 6. Golden suite

- [x] 6.1 Define case schema (JSON Schema or documented fields)
- [x] 6.2 Author ≥25 cases: happy, list-only, order traps, adversarial, multi-step, edge, regression
- [x] 6.3 Mark ≥8 cases `quick`
- [x] 6.4 Include `fixture_trajectory` (or linked fixture) for offline runs


## 7. Agent SUT (live, real AI)

- [x] 7.1 OpenAI-compatible client with tool_calls support
- [x] 7.2 Agent loop: system prompt + tools + max steps + trajectory log
- [x] 7.3 Save live runs to `reports/live_runs/`
- [x] 7.4 Clear handling of missing key / 429
- [x] 7.5 `@pytest.mark.live` smoke (skip without key)

## 8. Optional judge (L3)

- [x] 8.1 Judge module with rubric; `JUDGE_ENABLED=false` default
- [x] 8.2 Merge L3 into aggregate verdict only when enabled
- [x] 8.3 Meter counts judge calls

## 9. Eval runner

- [x] 9.1 `evals/run_suite.py --suite quick|full --mode fixture|live`
- [x] 9.2 Write `reports/last_run.json` + markdown summary
- [x] 9.3 Exit code non-zero on any FAIL (configurable) for CI


## 10. Trajectory Console (UI/UX)

- [x] 10.1 Design tokens CSS (light/dark, PASS/WARN/FAIL chips)
- [x] 10.2 **Suite Run** home: KPIs, run buttons, results table, taxonomy summary, mode badge
- [x] 10.3 **Cases** list with filters (tag, verdict)
- [x] 10.4 **Trajectory Detail**: vertical tool timeline, score card, side effects, raw JSON
- [x] 10.5 **Live Probe** (secondary): single input + presets + live steps + verdict
- [x] 10.6 **Reports** + **Setup** checklist (key, mode, judge, meter)
- [x] 10.7 Empty/error states; no chat-transcript home

## 11. Regression CI

- [x] 11.1 GitHub Actions: install, `pytest -m "not live"`, fixture quick suite
- [x] 11.2 Badge + status in README
- [x] 11.3 Document live opt-in for local only

## 12. Docs ship

- [x] 12.1 README quick start (fixture + live Groq)
- [x] 12.2 `docs/INTERVIEW.md` — 60–90s demo script
- [x] 12.3 `docs/ARCHITECTURE.md` — loop + scoring diagram
- [x] 12.4 Resume bullets verified against real repo behavior

