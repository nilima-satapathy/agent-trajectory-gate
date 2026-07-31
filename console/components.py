"""
Agent Trajectory Gate — unique "Night Circuit" UI system.

Deliberately different from QA Sentinel / ChainVerdict warm-paper labs:
  void canvas · acid lime + electric violet · hard geometry · mono-first path traces
"""

from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

from src.agent.types import AgentResult
from src.scoring.models import ScoreResult

# Night Circuit tokens — not warm cream, not teal Claude, not terracotta
NIGHT_CIRCUIT_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --void: #07080C;
  --panel: #0E1018;
  --panel-2: #141722;
  --line: #232838;
  --line-hot: #3D4560;
  --ink: #E8E6F0;
  --dim: #7A7E96;
  --ghost: #4A4E66;
  --lime: #C8F542;
  --lime-dim: rgba(200,245,66,.12);
  --violet: #A78BFA;
  --violet-hot: #7C3AED;
  --violet-dim: rgba(124,58,237,.18);
  --coral: #FF5C7A;
  --coral-dim: rgba(255,92,122,.14);
  --amber: #FFB020;
  --amber-dim: rgba(255,176,32,.14);
  --cyan: #22D3EE;
  --r: 4px;
  --font-display: 'Syne', system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
}

html, body, [class*="css"], .stApp, p, span, label, div, button {
  font-family: var(--font-mono) !important;
}

.stApp {
  background:
    radial-gradient(ellipse 80% 50% at 10% -10%, rgba(124,58,237,.18), transparent 50%),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(200,245,66,.06), transparent 45%),
    linear-gradient(180deg, #07080C 0%, #0A0C12 100%) !important;
  color: var(--ink) !important;
  background-attachment: fixed !important;
}

/* circuit grid overlay */
.stApp::before {
  content: '';
  pointer-events: none;
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(35,40,56,.55) 1px, transparent 1px),
    linear-gradient(90deg, rgba(35,40,56,.55) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 70% 60% at 50% 30%, black, transparent);
  z-index: 0;
  opacity: .55;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
div[data-testid="stToolbar"] { display: none; }

.block-container {
  padding: 1.1rem 1.4rem 3rem !important;
  max-width: 1180px;
  position: relative;
  z-index: 1;
}

/* —— Sidebar: solid slab, not soft cream —— */
section[data-testid="stSidebar"] {
  background: #080A10 !important;
  border-right: 1px solid var(--line) !important;
}
section[data-testid="stSidebar"] > div:first-child {
  background: #080A10 !important;
  padding-top: 1.1rem !important;
}
section[data-testid="stSidebar"] * {
  color: var(--ink) !important;
}
section[data-testid="stSidebar"] .stRadio label {
  font-size: 0.78rem !important;
  letter-spacing: 0.06em !important;
  text-transform: uppercase !important;
  padding: 0.35rem 0 !important;
}

/* form controls */
.stSelectbox label, .stTextInput label, .stTextArea label, .stRadio label {
  font-size: 0.68rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--dim) !important;
}
.stTextInput input, .stTextArea textarea {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
  color: var(--ink) !important;
  font-family: var(--font-mono) !important;
}

/* Selectboxes keep dropdown UI — hide text caret only */
div[data-baseweb="select"] > div {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
  color: var(--ink) !important;
  font-family: var(--font-mono) !important;
  cursor: pointer !important;
}
div[data-baseweb="select"] input,
div[data-testid="stSelectbox"] input,
div[data-baseweb="select"] [contenteditable="true"] {
  cursor: pointer !important;
  caret-color: transparent !important;
  color: transparent !important; /* hide caret flash; value still shown via value container */
  -webkit-text-fill-color: var(--ink) !important; /* keep visible label text */
  user-select: none !important;
}
/* Value label stays readable; input overlay should not show I-beam */
div[data-baseweb="select"] div[class*="valueContainer"],
div[data-baseweb="select"] span {
  cursor: pointer !important;
  caret-color: transparent !important;
  user-select: none !important;
}



.stButton > button {
  border-radius: var(--r) !important;
  font-family: var(--font-mono) !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  font-size: 0.72rem !important;
  border: 1px solid var(--line-hot) !important;
  background: var(--panel-2) !important;
  color: var(--ink) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: var(--lime) !important;
  color: #0A0B0F !important;
  border: 1px solid var(--lime) !important;
  box-shadow: 0 0 24px rgba(200,245,66,.25) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 0 32px rgba(200,245,66,.4) !important;
}

div[data-testid="stDataFrame"] {
  border: 1px solid var(--line) !important;
  border-radius: var(--r) !important;
  overflow: hidden;
}

/* ========== NIGHT CIRCUIT COMPONENTS ========== */

.nc-hero {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: end;
  margin-bottom: 1.5rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--line);
  position: relative;
}
.nc-hero::after {
  content: '';
  position: absolute;
  left: 0; bottom: -1px;
  width: 120px; height: 2px;
  background: linear-gradient(90deg, var(--lime), var(--violet-hot));
}
.nc-kicker {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--violet);
  margin: 0 0 0.45rem;
}
.nc-title {
  font-family: var(--font-display) !important;
  font-size: clamp(1.6rem, 3vw, 2.15rem);
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 0.95;
  margin: 0;
  color: var(--ink);
  text-transform: uppercase;
}
.nc-title em {
  font-style: normal;
  color: var(--lime);
  text-shadow: 0 0 40px rgba(200,245,66,.35);
}
.nc-sub {
  margin: 0.55rem 0 0;
  font-size: 0.78rem;
  color: var(--dim);
  max-width: 36rem;
  line-height: 1.5;
  letter-spacing: 0.02em;
}
.nc-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.4rem;
}

/* stamps / badges — hard, not soft pills */
.stamp {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.28rem 0.55rem;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  border: 1px solid;
  border-radius: 2px;
  line-height: 1;
}
.stamp-pass { color: var(--lime); border-color: var(--lime); background: var(--lime-dim); }
.stamp-warn { color: var(--amber); border-color: var(--amber); background: var(--amber-dim); }
.stamp-fail { color: var(--coral); border-color: var(--coral); background: var(--coral-dim); }
.stamp-skip { color: var(--dim); border-color: var(--line-hot); background: transparent; }
.stamp-tax  { color: var(--violet); border-color: var(--violet); background: var(--violet-dim); }
.stamp-mode { color: var(--cyan); border-color: var(--cyan); background: rgba(34,211,238,.1); }
.stamp-lg {
  font-size: 0.95rem;
  padding: 0.45rem 0.75rem;
  letter-spacing: 0.18em;
  transform: rotate(-2deg);
  box-shadow: 4px 4px 0 rgba(0,0,0,.35);
}

/* KPI instruments */
.nc-kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
  margin: 0 0 1.35rem;
}
.nc-kpi {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 0.9rem 0.85rem 0.75rem;
  position: relative;
  overflow: hidden;
}
.nc-kpi::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--line-hot);
}
.nc-kpi.k-pass::before { background: var(--lime); box-shadow: 0 0 12px var(--lime); }
.nc-kpi.k-warn::before { background: var(--amber); }
.nc-kpi.k-fail::before { background: var(--coral); box-shadow: 0 0 12px rgba(255,92,122,.5); }
.nc-kpi.k-all::before { background: linear-gradient(90deg, var(--violet-hot), var(--lime)); }
.nc-kpi .lbl {
  font-size: 0.58rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ghost);
  margin-bottom: 0.35rem;
}
.nc-kpi .val {
  font-family: var(--font-display) !important;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
  color: var(--ink);
}
.nc-kpi.k-pass .val { color: var(--lime); }
.nc-kpi.k-warn .val { color: var(--amber); }
.nc-kpi.k-fail .val { color: var(--coral); }

/* taxonomy ticks */
.nc-tax {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 0 0 1.25rem;
}
.nc-tax-item {
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  padding: 0.3rem 0.55rem;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--dim);
  border-radius: 2px;
}
.nc-tax-item b {
  color: var(--violet);
  font-weight: 700;
  margin-right: 0.35rem;
}

/* section slash headers */
.nc-sec {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin: 1.35rem 0 0.7rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--dim);
}
.nc-sec::before {
  content: '//';
  color: var(--lime);
  letter-spacing: 0;
}
.nc-sec::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

/* HORIZONTAL TRACE — unique vs vertical card stacks elsewhere */
.trace {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 1.1rem 1rem 0.85rem;
  margin: 0.5rem 0 1rem;
  overflow-x: auto;
}
.trace-rail {
  display: flex;
  align-items: stretch;
  gap: 0;
  min-width: min-content;
  padding-bottom: 0.25rem;
}
.trace-node {
  flex: 0 0 auto;
  width: 148px;
  position: relative;
}
.trace-node:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 18px;
  left: 36px;
  right: -8px;
  height: 2px;
  background: linear-gradient(90deg, var(--violet), var(--line-hot));
  z-index: 0;
}
.trace-node.is-ok:not(:last-child)::after {
  background: linear-gradient(90deg, var(--lime), var(--violet));
}
.trace-node.is-bad:not(:last-child)::after {
  background: linear-gradient(90deg, var(--coral), var(--line-hot));
}
.trace-node.is-final:not(:last-child)::after { display: none; }

.trace-orb {
  width: 36px; height: 36px;
  border-radius: 2px;
  border: 1px solid var(--violet);
  background: var(--void);
  color: var(--violet);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  position: relative;
  z-index: 1;
  margin-bottom: 0.55rem;
  transform: rotate(45deg);
}
.trace-orb span { transform: rotate(-45deg); display: block; }
.trace-node.is-ok .trace-orb {
  border-color: var(--lime); color: var(--lime);
  box-shadow: 0 0 16px rgba(200,245,66,.25);
}
.trace-node.is-bad .trace-orb {
  border-color: var(--coral); color: var(--coral);
  box-shadow: 0 0 16px rgba(255,92,122,.3);
}
.trace-node.is-final .trace-orb {
  border-color: var(--cyan); color: var(--cyan);
  border-radius: 50%;
  transform: none;
}
.trace-node.is-final .trace-orb span { transform: none; }

.trace-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--ink);
  word-break: break-word;
  line-height: 1.3;
  margin-bottom: 0.3rem;
}
.trace-args {
  font-size: 0.58rem;
  color: var(--ghost);
  line-height: 1.4;
  max-height: 4.2rem;
  overflow: hidden;
  word-break: break-all;
}
.trace-final-txt {
  font-size: 0.72rem;
  color: var(--dim);
  line-height: 1.4;
  max-width: 220px;
}

/* inspect split */
.nc-panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 1rem 1.05rem;
  margin-bottom: 0.75rem;
}
.nc-panel-h {
  font-size: 0.6rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ghost);
  margin: 0 0 0.65rem;
}
.nc-quote {
  border-left: 2px solid var(--lime);
  padding: 0.5rem 0 0.5rem 0.75rem;
  font-size: 0.82rem;
  color: var(--ink);
  line-height: 1.45;
  background: linear-gradient(90deg, var(--lime-dim), transparent);
}
.nc-expect {
  font-size: 0.68rem;
  color: var(--dim);
  margin: 0.35rem 0;
  line-height: 1.4;
}
.nc-expect i {
  font-style: normal;
  color: var(--violet);
  margin-right: 0.4rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 0.58rem;
}

/* score instrument */
.nc-score {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 1rem;
  position: relative;
  overflow: hidden;
}
.nc-score::after {
  content: 'GATE';
  position: absolute;
  right: -0.2rem;
  bottom: -0.4rem;
  font-family: var(--font-display) !important;
  font-size: 3.5rem;
  font-weight: 800;
  color: rgba(255,255,255,.03);
  letter-spacing: -0.04em;
  pointer-events: none;
}
.nc-layers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4rem;
  margin: 0.85rem 0 0.75rem;
}
.nc-layer {
  text-align: center;
  padding: 0.55rem 0.25rem;
  border: 1px solid var(--line);
  background: var(--void);
  border-radius: 2px;
}
.nc-layer .ly {
  font-size: 0.55rem;
  letter-spacing: 0.12em;
  color: var(--ghost);
  text-transform: uppercase;
}
.nc-layer .st {
  font-family: var(--font-display) !important;
  font-size: 0.85rem;
  font-weight: 700;
  margin-top: 0.25rem;
  letter-spacing: 0.04em;
}
.s-pass { color: var(--lime); }
.s-warn { color: var(--amber); }
.s-fail { color: var(--coral); }
.s-skip { color: var(--ghost); }
.nc-rationale {
  font-size: 0.72rem;
  color: var(--dim);
  line-height: 1.45;
  border-top: 1px solid var(--line);
  padding-top: 0.65rem;
}

/* empty */
.nc-empty {
  border: 1px dashed var(--line-hot);
  background:
    repeating-linear-gradient(
      -45deg,
      transparent,
      transparent 8px,
      rgba(124,58,237,.04) 8px,
      rgba(124,58,237,.04) 16px
    ),
    var(--panel);
  padding: 2.75rem 1.5rem;
  text-align: center;
  border-radius: var(--r);
}
.nc-empty .glyph {
  font-family: var(--font-display) !important;
  font-size: 2rem;
  color: var(--lime);
  margin-bottom: 0.65rem;
  text-shadow: 0 0 24px rgba(200,245,66,.4);
}
.nc-empty .msg {
  font-size: 0.85rem;
  color: var(--dim);
  line-height: 1.55;
  max-width: 28rem;
  margin: 0 auto;
}
.nc-empty .cta {
  margin-top: 1rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--lime);
}

/* checklist */
.nc-check {
  display: flex;
  gap: 0.65rem;
  align-items: flex-start;
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--line);
  background: var(--panel);
  margin-bottom: 0.35rem;
  font-size: 0.78rem;
  color: var(--ink);
  border-radius: 2px;
}
.nc-check .mk {
  font-weight: 700;
  width: 1rem;
  flex-shrink: 0;
}
.mk-ok { color: var(--lime); }
.mk-no { color: var(--coral); }

/* sidebar brand */
.nc-sb {
  margin-bottom: 1.1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--line);
}
.nc-sb-mark {
  width: 36px; height: 36px;
  background: var(--void);
  border: 1px solid var(--lime);
  color: var(--lime);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display) !important;
  font-weight: 800;
  font-size: 1.1rem;
  margin-bottom: 0.65rem;
  box-shadow: 4px 4px 0 var(--violet-hot);
}
.nc-sb-name {
  font-family: var(--font-display) !important;
  font-weight: 800;
  font-size: 0.95rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink);
  line-height: 1.1;
}
.nc-sb-name span { color: var(--lime); }
.nc-sb-tag {
  font-size: 0.62rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ghost);
  margin-top: 0.35rem;
  line-height: 1.4;
}

/* bug chips */
.nc-bug {
  border: 1px solid var(--line);
  background: var(--void);
  padding: 0.55rem 0.65rem;
  margin-bottom: 0.4rem;
  border-radius: 2px;
}
.nc-bug .id {
  color: var(--lime);
  font-size: 0.75rem;
  font-weight: 700;
}
.nc-bug .meta {
  font-size: 0.65rem;
  color: var(--dim);
  margin-top: 0.2rem;
}

/* hide streamlit branding noise */
[data-testid="stDecoration"] { display: none; }
</style>
"""

# JS: kill caret on BaseWeb select inputs (Streamlit selectbox)
_NO_CARET_JS = """
<script>
(function () {
  function killCaret(root) {
    if (!root) return;
    root.querySelectorAll('div[data-baseweb="select"] input, div[data-testid="stSelectbox"] input').forEach(function (el) {
      el.setAttribute('readonly', 'readonly');
      el.style.caretColor = 'transparent';
      el.style.cursor = 'pointer';
      el.addEventListener('mousedown', function (e) {
        // keep dropdown open behavior; prevent text selection caret
        el.blur();
      }, true);
      el.addEventListener('focus', function () {
        el.style.caretColor = 'transparent';
        // move caret away without blocking open
        try { el.setSelectionRange(0, 0); } catch (err) {}
      });
    });
  }
  const doc = window.parent && window.parent.document ? window.parent.document : document;
  killCaret(doc);
  const obs = new MutationObserver(function () { killCaret(doc); });
  obs.observe(doc.body, { childList: true, subtree: true });
})();
</script>
"""


def inject_css(dark: bool = False) -> None:
    """Always Night Circuit — light toggle ignored for identity consistency."""
    _ = dark  # reserved; product identity is dark-only
    st.markdown(NIGHT_CIRCUIT_CSS, unsafe_allow_html=True)
    # Hide I-beam caret on dropdowns while keeping select UI
    st.markdown(_NO_CARET_JS, unsafe_allow_html=True)



def esc(text: Any) -> str:
    return html.escape(str(text if text is not None else ""))


def chip(text: str, kind: str = "skip") -> str:
    """Stamp badges (not soft rounded pills like other portfolio apps)."""
    kind_l = (kind or "skip").lower()
    kind_u = kind_l.upper()
    cls_map = {
        "pass": "stamp-pass",
        "warn": "stamp-warn",
        "fail": "stamp-fail",
        "skip": "stamp-skip",
        "tax": "stamp-tax",
        "mode": "stamp-mode",
        "indigo": "stamp-mode",
    }
    if kind_u in ("PASS", "WARN", "FAIL", "SKIP"):
        cls = f"stamp-{kind_l}"
    else:
        cls = cls_map.get(kind_l, "stamp-skip")
    return f'<span class="stamp {cls}">{esc(text)}</span>'


def page_header(
    title: str,
    subtitle: str,
    *,
    pills_html: str = "",
    kicker: str = "AGENT TRAJECTORY GATE",
) -> None:
    # Allow *lime* emphasis via wrapping last word if title has pipe
    if "|" in title:
        a, b = title.split("|", 1)
        title_html = f"{esc(a.strip())} <em>{esc(b.strip())}</em>"
    else:
        title_html = esc(title)
    st.markdown(
        f"""
<div class="nc-hero">
  <div>
    <p class="nc-kicker">{esc(kicker)}</p>
    <h1 class="nc-title">{title_html}</h1>
    <p class="nc-sub">{esc(subtitle)}</p>
  </div>
  <div class="nc-meta">{pills_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpis(counts: dict[str, int]) -> None:
    parts = ['<div class="nc-kpis">']
    for key, label, cls in (
        ("cases", "SIGNAL COUNT", "k-all"),
        ("PASS", "CLEARED", "k-pass"),
        ("WARN", "AMBER", "k-warn"),
        ("FAIL", "BLOCKED", "k-fail"),
    ):
        n = counts.get(key, 0)
        parts.append(
            f'<div class="nc-kpi {cls}"><div class="lbl">{label}</div>'
            f'<div class="val">{n}</div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_taxonomy(tax: dict[str, int]) -> None:
    if not tax:
        return
    st.markdown('<div class="nc-sec">Taxonomy spectrum</div>', unsafe_allow_html=True)
    bits = ['<div class="nc-tax">']
    for k, v in sorted(tax.items(), key=lambda kv: (-kv[1], kv[0])):
        bits.append(
            f'<span class="nc-tax-item"><b>{esc(k)}</b>{v}</span>'
        )
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


def render_score_card(score: ScoreResult) -> None:
    l3 = score.l3.status if score.l3 else "SKIP"

    def sc(s: str) -> str:
        s = (s or "SKIP").upper()
        return {"PASS": "s-pass", "WARN": "s-warn", "FAIL": "s-fail"}.get(s, "s-skip")

    stamp = chip(score.verdict, score.verdict)
    # large rotated stamp feel
    stamp_lg = stamp.replace('class="stamp ', 'class="stamp stamp-lg ')
    st.markdown(
        f"""
<div class="nc-score">
  <div style="display:flex;gap:.5rem;flex-wrap:wrap;align-items:center">
    {stamp_lg}
    {chip(score.taxonomy_label or "—", "tax")}
  </div>
  <div class="nc-layers">
    <div class="nc-layer"><div class="ly">L1 path</div>
      <div class="st {sc(score.l1.status)}">{esc(score.l1.status)}</div></div>
    <div class="nc-layer"><div class="ly">L2 answer</div>
      <div class="st {sc(score.l2.status)}">{esc(score.l2.status)}</div></div>
    <div class="nc-layer"><div class="ly">L3 judge</div>
      <div class="st {sc(l3)}">{esc(l3)}</div></div>
  </div>
  <div class="nc-rationale">{esc(score.taxonomy_rationale or "Path clear. Gate open.")}</div>
  {_llm_block(score)}
</div>
""",
        unsafe_allow_html=True,
    )


def _llm_block(score: ScoreResult) -> str:
    """Show LLM trajectory judge summary inside the score card (no gate-log spam)."""
    l3 = score.l3.status if score.l3 else "SKIP"
    if l3 == "SKIP" and not score.l3_summary:
        return (
            '<div class="nc-rationale" style="margin-top:.55rem;border-top:1px solid var(--line);'
            'padding-top:.55rem;color:var(--ghost)">'
            "LLM trajectory judge: skipped (set OPENAI_API_KEY + JUDGE_ENABLED=true)"
            "</div>"
        )
    score_bit = (
        f"score {score.l3_score}/5 · "
        if score.l3_score is not None
        else ""
    )
    path_bit = ""
    if score.l3_path_ok is True:
        path_bit = "path_ok · "
    elif score.l3_path_ok is False:
        path_bit = "path_fail · "
    primary = (
        f"[{esc(score.l3_primary_failure)}] "
        if score.l3_primary_failure
        else ""
    )
    summary = esc(score.l3_summary or "—")
    return (
        f'<div class="nc-rationale" style="margin-top:.55rem;border-top:1px solid var(--line);'
        f'padding-top:.55rem">'
        f'<span style="color:var(--violet);letter-spacing:.1em;font-size:.58rem;'
        f'text-transform:uppercase;font-weight:700">LLM trajectory judge</span><br/>'
        f"{score_bit}{path_bit}{primary}{summary}"
        f"</div>"
    )




def render_timeline(result: AgentResult) -> None:
    """Horizontal circuit trace — signature element, not vertical chat-like stack."""
    st.markdown('<div class="nc-sec">Path trace</div>', unsafe_allow_html=True)
    if not result.trajectory:
        st.caption("No hops recorded.")
        return

    nodes = ['<div class="trace"><div class="trace-rail">']
    for step in result.trajectory:
        if step.kind == "tool":
            ok = (step.result or {}).get("ok")
            cls = "is-ok" if ok else "is-bad"
            mark = "OK" if ok else "!!"
            args = json.dumps(step.args or {}, ensure_ascii=False)
            if len(args) > 90:
                args = args[:87] + "…"
            nodes.append(
                f"""
<div class="trace-node {cls}">
  <div class="trace-orb"><span>{esc(mark)}</span></div>
  <div class="trace-label">{esc(step.step)} · {esc(step.tool)}</div>
  <div class="trace-args">{esc(args)}</div>
</div>"""
            )
        else:
            content = step.content or result.final_answer or ""
            if len(content) > 140:
                content = content[:137] + "…"
            nodes.append(
                f"""
<div class="trace-node is-final">
  <div class="trace-orb"><span>END</span></div>
  <div class="trace-label">{esc(step.step)} · final</div>
  <div class="trace-final-txt">{esc(content)}</div>
</div>"""
            )
    nodes.append("</div></div>")
    st.markdown("".join(nodes), unsafe_allow_html=True)


def render_detail(
    case: dict[str, Any],
    result: AgentResult,
    score: ScoreResult,
) -> None:
    st.markdown(
        f'<div class="nc-sec">Inspect · {esc(case.get("id"))}</div>',
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.3, 1], gap="medium")
    with left:
        exp = case.get("expected") or {}
        exp_html = ""
        if exp.get("must_call_tools"):
            exp_html += (
                f'<div class="nc-expect"><i>must</i>'
                f'{esc(", ".join(exp["must_call_tools"]))}</div>'
            )
        if exp.get("must_not_call_tools"):
            exp_html += (
                f'<div class="nc-expect"><i>forbid</i>'
                f'{esc(", ".join(exp["must_not_call_tools"]))}</div>'
            )
        if exp.get("order_constraints"):
            exp_html += (
                f'<div class="nc-expect"><i>order</i>'
                f'{esc(exp["order_constraints"])}</div>'
            )
        st.markdown(
            f"""
<div class="nc-panel">
  <div class="nc-panel-h">Input signal</div>
  <div class="nc-quote">{esc(result.input)}</div>
  {exp_html}
</div>
""",
            unsafe_allow_html=True,
        )
        render_timeline(result)

    with right:
        st.markdown(
            '<div class="nc-panel-h">Verdict instrument</div>',
            unsafe_allow_html=True,
        )
        render_score_card(score)




def empty_state(message: str, cta: str = "", icon: str = "◎") -> None:
    extra = f'<div class="cta">{esc(cta)}</div>' if cta else ""
    # message may contain safe <strong>/<code> from callers — keep limited
    st.markdown(
        f"""
<div class="nc-empty">
  <div class="glyph">{esc(icon)}</div>
  <div class="msg">{message}</div>
  {extra}
</div>
""",
        unsafe_allow_html=True,
    )


def checklist_row(ok: bool, label: str) -> str:
    mk = "●" if ok else "○"
    cls = "mk-ok" if ok else "mk-no"
    return (
        f'<div class="nc-check"><span class="mk {cls}">{mk}</span>'
        f"{esc(label)}</div>"
    )
