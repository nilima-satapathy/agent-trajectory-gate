# Architecture — Agent Trajectory Gate

## Product truth

```text
Engineer defines tools  →  LLM calls tools (or fixture replays)  →  Harness scores the path
```

The agent does **not** invent tools. Tools live in `src/tools/`.

## High-level

```text
                    ┌─────────────────────┐
                    │ golden/fixture_cases│
                    └──────────┬──────────┘
                               ▼
┌──────────────┐     run(case)         ┌──────────────────────────┐
│ evals/runner │ ────────────────────► │ FixtureSUT | LiveAgentSUT│
│ console UI   │                       └────────────┬─────────────┘
└──────────────┘                                    │
                                                    │ AgentResult
                                                    │ (trajectory + answer + store)
                                                    ▼
                                           ┌────────────────┐
                                           │ L1 path score  │
                                           │ L2 answer      │
                                           │ L3 judge (opt) │
                                           └────────┬───────┘
                                                    ▼
                                           taxonomy + PASS/WARN/FAIL
                                                    │
                     ┌──────────────────────────────┼──────────────────┐
                     ▼                              ▼                  ▼
              reports/*.json               Trajectory Console     Pytest / GHA
```

## Live agent loop

```text
messages = [system, user]
for step in 1..MAX_TOOL_STEPS:
  resp = llm.chat(messages, tools=registry.schemas)   # Groq OpenAI-compatible
  if resp.tool_calls:
    for call in resp.tool_calls:
      result = registry.execute(call.name, call.args)
      append tool message; log TrajectoryStep
  else:
    return final_answer + trajectory
```

## Scoring layers

| Layer | Cost | Role |
|-------|------|------|
| L1 | Free | Required/forbidden tools, order, args, hallucinated tools, state, step budget |
| L2 | Free | Answer must-include, answer lies, forbidden phrases |
| L3 | Free-tier call | Optional rubric judge (`JUDGE_ENABLED`) |

Policy: `config/scoring.yaml`.

## Taxonomy priority (primary label)

`MODEL_ERROR` → `HALLUCINATED_TOOL` → `INFINITE_LOOP` → `MISSING_TOOL` → `ORDER_ERROR` → `BAD_ARGS` → `STATE_MISMATCH` → `WRONG_TOOL` → `ANSWER_LIE` → …

## Package map

```text
src/tools/     author-defined registry + store
src/agent/     prompts, loop, types, persist
src/llm/       fixture + live SUT + client
src/scoring/   L1, L2, taxonomy, aggregate
src/judge/     optional L3
src/meter/     free-tier usage
console/       Streamlit lab UI
golden/        cases + schema
evals/         batch runner
tests/         offline first; @pytest.mark.live opt-in
```

## Differentiation

| Project | SUT |
|---------|-----|
| DocQ / QA Sentinel | Chat / answer gate |
| ChainVerdict | LangChain RAG |
| **This** | **Tool-calling agent trajectory** |
