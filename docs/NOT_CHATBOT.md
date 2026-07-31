# Not a chatbot product

**Agent Trajectory Gate** is an **AI testing lab** for tool-calling agents.  
If a PR or demo makes this feel like DocQ or QA Sentinel chat-home, reject it.

## Checklist for PRs and demos

- [ ] Default UI is **Suite Run** (KPIs, run suite, results table) — not a chat transcript
- [ ] Hero artifact is a **tool trajectory timeline**, not only the final answer bubble
- [ ] README lead says **agents under test / trajectory gate**, not “ask me anything”
- [ ] Tools are **author-defined** in code; model does not create tools at runtime
- [ ] Live Probe is **secondary** navigation (real Groq demo), not the only home
- [ ] Failure taxonomy uses agent classes (`MISSING_TOOL`, `BAD_ARGS`, …) not only “bad answer”
- [ ] CI default path is **fixture / offline** without API keys
- [ ] Differentiation table vs DocQ / QA Sentinel / ChainVerdict remains accurate

## Acceptable live UX

- Single-case **Live Probe** with step list + verdict
- Suite mode `live` with free-tier meter

## Not acceptable as MVP home

- Multi-turn chat as the only landing experience
- Hiding trajectory behind “expand raw JSON” only
- Marketing copy that says “chatbot with quality scores” without path scoring
