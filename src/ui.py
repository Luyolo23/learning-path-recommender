"""Presentation helpers: CSS and small HTML builders for the Streamlit app.

All dynamic text is escaped with html.escape, and links are only allowed to be
http(s), so catalogue or LLM text can never inject markup into the page.
"""
from __future__ import annotations

import html

from .config import TOPIC_LABELS, TOPICS

# Olive-themed topic colors — earthy, warm palette
TOPIC_COLORS = {
    "python": "#6B7821",   # olive green
    "data": "#8B6914",     # dark golden
    "prompting": "#5E6E3F", # sage
    "ml": "#9B7B2C",       # warm bronze
    "evaluation": "#4E6B4A", # forest
    "ethics": "#7A6B3A",   # earthy brown-olive
}
TOPIC_ICONS = {
    "python": "🐍", "data": "📊", "prompting": "💬",
    "ml": "🤖", "evaluation": "🎯", "ethics": "⚖️",
}
LEVELS = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}

# ────────────────────────────────────────────────────────────────────────── #
#  Olive theme palette
# ────────────────────────────────────────────────────────────────────────── #
# PRIMARY   = #6B7821  (deep olive)
# SECONDARY = #8B9D3E  (warm olive)
# ACCENT    = #AAB84A  (bright olive)
# DARK      = #3A4212  (very dark olive)
# LIGHT BG  = #F8F7F2  (warm off-white)
# BORDER    = #D5D0B8  (warm tan border)

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ──── Global typography ──── */
html, body, [class*="css"], .stMarkdown, .stTabs [data-baseweb="tab-panel"],
.stTabs [data-baseweb="tab"], .stButton > button, .stTextInput > div > div > input,
.stSlider, .stSelectbox, .stCaption, .stRadio label, p, span, li, td, th {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.block-container { padding-top: 2rem; max-width: 1150px; }

/* ──── Hero banner ──── */
.hero {
    padding: 2rem 2.2rem; border-radius: 20px; color: #fff; margin-bottom: 1.4rem;
    background: linear-gradient(135deg, #3A4212 0%, #6B7821 40%, #8B9D3E 75%, #AAB84A 100%);
    box-shadow: 0 8px 32px rgba(58,66,18,.18);
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; top: -50%; right: -30%; width: 70%; height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero h1 {
    margin: 0; font-size: 2.1rem; color: #fff; padding: 0;
    font-weight: 800; letter-spacing: -.02em; position: relative; z-index: 1;
}
.hero p {
    margin: .45rem 0 0; font-size: 1.05rem; opacity: .92;
    position: relative; z-index: 1; font-weight: 400;
}

/* ──── Stepper ──── */
.stepper { display: flex; gap: .65rem; margin: .2rem 0 1.4rem; }
.step {
    flex: 1; padding: .6rem 1rem; border-radius: 14px; font-size: .88rem;
    border: 1.5px solid rgba(107,120,33,.20); opacity: .55;
    background: rgba(107,120,33,.03); transition: all .2s ease;
}
.step.active {
    opacity: 1; border-color: #6B7821;
    background: rgba(107,120,33,.10);
    font-weight: 700; color: #3A4212;
    box-shadow: 0 2px 8px rgba(107,120,33,.12);
}
.step.done {
    opacity: 1; border-color: #4E6B4A;
    background: rgba(78,107,74,.08);
    color: #4E6B4A;
}

/* ──── KPI cards ──── */
.kpi {
    border: 1.5px solid #D5D0B8; border-radius: 16px; padding: .9rem 1.1rem; height: 100%;
    background: linear-gradient(145deg, rgba(248,247,242,.9) 0%, rgba(213,208,184,.12) 100%);
    transition: transform .2s ease, box-shadow .2s ease;
}
.kpi:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(107,120,33,.10);
}
.kpi .label {
    font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
    opacity: .65; font-weight: 600; color: #6B7821;
}
.kpi .value {
    font-size: 1.4rem; font-weight: 800; line-height: 1.25; margin-top: .2rem;
    color: #3A4212;
}
.kpi .sub { font-size: .82rem; opacity: .6; margin-top: .12rem; font-weight: 500; }

/* ──── Skill bars ──── */
.skill { margin-bottom: .7rem; }
.skill-top {
    display: flex; justify-content: space-between; font-size: .88rem;
    margin-bottom: .25rem; font-weight: 500;
}
.track {
    height: 10px; border-radius: 99px;
    background: rgba(107,120,33,.10); overflow: hidden;
}
.fill {
    height: 100%; border-radius: 99px;
    transition: width .6s cubic-bezier(.4,0,.2,1);
}

/* ──── Badges ──── */
.badge {
    display: inline-block; padding: .15rem .65rem; border-radius: 999px;
    font-size: .73rem; font-weight: 600; margin: 0 .35rem .35rem 0;
    transition: transform .15s ease;
}
.badge:hover { transform: scale(1.04); }
.badge.plain {
    background: rgba(107,120,33,.08);
    color: #5E6E3F; border: 1px solid rgba(107,120,33,.18);
}

/* ──── Resource cards ──── */
.rcard {
    border: 1.5px solid #D5D0B8; border-left: 6px solid var(--c); border-radius: 16px;
    padding: .95rem 1.2rem; margin-bottom: .8rem;
    background: rgba(248,247,242,.5);
    transition: transform .2s ease, box-shadow .2s ease;
}
.rcard:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 22px rgba(107,120,33,.10);
}
.rcard .top { display: flex; align-items: baseline; gap: .65rem; }
.rcard .num { font-weight: 800; font-size: 1.2rem; color: var(--c); }
.rcard .title { font-weight: 700; font-size: 1.04rem; color: #3A4212; }
.rcard .prov { opacity: .6; font-size: .84rem; margin: .15rem 0 .45rem; font-weight: 500; }
.rcard .why { font-size: .9rem; opacity: .85; margin: .3rem 0 .5rem; line-height: 1.5; }
.rcard a {
    font-size: .88rem; font-weight: 700; text-decoration: none;
    color: #6B7821; border-bottom: 2px solid rgba(107,120,33,.25);
    transition: border-color .2s ease;
}
.rcard a:hover { border-color: #6B7821; }

/* ──── Learner type box ──── */
.typebox {
    border-radius: 16px; padding: 1.1rem 1.3rem;
    background: rgba(107,120,33,.07);
    border: 1.5px solid rgba(107,120,33,.22);
}
.typebox .name {
    font-weight: 800; font-size: 1.1rem; margin-bottom: .35rem;
    color: #3A4212;
}

/* ──── Sidebar refinements ──── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #F8F7F2 0%, #F0EDE0 100%);
    border-right: 1.5px solid #D5D0B8;
}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
    padding-top: .5rem;
}

/* ──── Tabs ──── */
.stTabs [data-baseweb="tab-list"] {
    gap: .3rem;
    border-bottom: 2px solid rgba(107,120,33,.12);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0;
    padding: .55rem 1rem;
    font-weight: 600; font-size: .88rem;
}
.stTabs [aria-selected="true"] {
    border-bottom: 3px solid #6B7821 !important;
    color: #3A4212 !important;
}

/* ──── Primary button ──── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #6B7821, #8B9D3E) !important;
    color: #fff !important; border: none !important;
    font-weight: 700 !important; border-radius: 12px !important;
    padding: .55rem 1.6rem !important;
    box-shadow: 0 4px 14px rgba(107,120,33,.20) !important;
    transition: all .2s ease !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    box-shadow: 0 6px 20px rgba(107,120,33,.28) !important;
    transform: translateY(-1px) !important;
}

/* ──── Secondary buttons ──── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    border-color: #D5D0B8 !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    border-color: #6B7821 !important;
    color: #3A4212 !important;
}

/* ──── Download button ──── */
.stDownloadButton > button {
    background: rgba(107,120,33,.08) !important;
    border: 1.5px solid rgba(107,120,33,.22) !important;
    color: #3A4212 !important;
    border-radius: 12px !important; font-weight: 600 !important;
    transition: all .2s ease !important;
}
.stDownloadButton > button:hover {
    background: rgba(107,120,33,.15) !important;
    border-color: #6B7821 !important;
}

/* ──── Progress bar ──── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #6B7821, #AAB84A) !important;
    border-radius: 99px;
}

/* ──── Expander ──── */
.streamlit-expanderHeader {
    font-weight: 600 !important;
    color: #3A4212 !important;
}

/* ──── Smooth link hover on the entire page ──── */
a { transition: color .2s ease; }
</style>
"""


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def safe_url(url: str) -> str | None:
    url = str(url).strip()
    return url if url.lower().startswith(("http://", "https://")) else None


def hero_html(title: str, subtitle: str) -> str:
    return f'<div class="hero"><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div>'


def stepper_html(active: int) -> str:
    """active: 1 = quiz, 2 = results."""
    labels = ["1 · Take the quiz", "2 · See your profile and path", "3 · Follow your plan"]
    out = []
    for i, label in enumerate(labels, start=1):
        cls = "done" if i < active else ("active" if i == active else "")
        out.append(f'<div class="step {cls}">{"✓ " if i < active else ""}{esc(label)}</div>')
    return '<div class="stepper">' + "".join(out) + "</div>"


def kpi_html(label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="sub">{esc(sub)}</div>' if sub else ""
    return (f'<div class="kpi"><div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div>{sub_html}</div>')


def badge_html(text: str, color: str | None = None) -> str:
    if color:
        return (f'<span class="badge" style="background:{color}18;color:{color};'
                f'border:1px solid {color}40">{esc(text)}</span>')
    return f'<span class="badge plain">{esc(text)}</span>'


def skill_bars_html(skills: dict[str, float]) -> str:
    rows = []
    for t in TOPICS:
        pct = int(round(skills[t] * 100))
        rows.append(
            f'<div class="skill"><div class="skill-top"><span>{TOPIC_ICONS[t]} {esc(TOPIC_LABELS[t])}</span>'
            f'<b>{pct}%</b></div><div class="track"><div class="fill" '
            f'style="width:{max(pct, 2)}%;background:{TOPIC_COLORS[t]}"></div></div></div>'
        )
    return "".join(rows)


def resource_card_html(item: dict) -> str:
    """item: a row of the recommendations table (as a dict)."""
    color = TOPIC_COLORS[item["topic"]]
    badges = (badge_html(f'{TOPIC_ICONS[item["topic"]]} {TOPIC_LABELS[item["topic"]]}', color)
              + badge_html(LEVELS[int(item["difficulty"])])
              + badge_html(str(item["format"]))
              + badge_html(f'{float(item["hours"]):g} h'))
    url = safe_url(item["url"])
    link = (f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Open resource ↗</a>'
            if url else "")
    return (
        f'<div class="rcard" style="--c:{color}">'
        f'<div class="top"><span class="num">{int(item["order"])}</span>'
        f'<span class="title">{esc(item["title"])}</span></div>'
        f'<div class="prov">{esc(item["provider"])}</div>{badges}'
        f'<div class="why">{esc(item["reason"])}</div>{link}</div>'
    )
