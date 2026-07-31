# Interview demo — Agent Trajectory Gate (60–90 seconds)

## One-liner

> I built a lab that scores **tool-calling agents** on the **path** they take — which tools, in what order, with what args — not just whether the final sentence looks good. Offline fixtures for CI; free-tier Groq for live demos.

## 60-second path (recommended)

1. Open **http://localhost:8501** → **Suite Run** (not chat).
2. Click **Run suite** (quick / fixture).
3. Point at KPI cards: PASS / WARN / FAIL.
4. Select a **FAIL** case (e.g. `triage-fail-missing-tool`).
5. Show **timeline**: only `search_known_issues` — missing `create_bug` / `assign_owner`.
6. Score card: **L1 FAIL** + taxonomy **`MISSING_TOOL`** + **ANSWER_LIE** secondary.
7. Optional: **Cases** tab → filter `fail_demo` / `happy`.
8. Optional: **Setup** → key checklist + free-tier meter.

## 90-second path (+ live)

1. Do the 60s fixture story.
2. **Live Probe** → preset “Happy create+assign” → **Run live agent** (needs Groq key).
3. Show real tool steps + saved file under `reports/live_runs/`.
4. Contrast: *fixture proves the gate; live proves the agent under a real free model.*

## CLI backup (no UI)

```powershell
cd C:\Users\admin\Code\agent-trajectory-gate
.\.venv\Scripts\activate
pytest tests/ -q -m "not live"
python evals/run_suite.py --suite quick --mode fixture
```

Open `reports/last_run.md`.

## Questions you should invite

| Question | Answer cue |
|----------|------------|
| Why not only score the answer? | Agents take **actions**; wrong path can still “sound” right. |
| How is this different from RAG eval? | SUT is **tool loop**, not retrieve→generate. |
| CI without burning credits? | `SUT_MODE=fixture` + GitHub Actions `not live`. |
| What does taxonomy give you? | Root cause: MISSING_TOOL vs BAD_ARGS vs ANSWER_LIE. |

## Resume bullets (verified against repo)

- Built **Agent Trajectory Gate**, an AI Test Engineer lab that scores multi-step tool-calling agents on trajectory correctness (required tools, order, arguments, side effects) with free-tier Groq live runs and offline CI fixtures.
- Implemented L1 path gates + L2 answer-lie checks + failure taxonomy (`MISSING_TOOL`, `ORDER_ERROR`, `HALLUCINATED_TOOL`, …) and a Streamlit trajectory inspector.
- Shipped Pytest suite (offline), GitHub Actions CI, and batch runner writing `reports/last_run.json` for ship/no-ship evidence.
