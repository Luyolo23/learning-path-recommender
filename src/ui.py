"""Presentation helpers: CSS and small HTML builders for the Streamlit app.

All dynamic text is escaped with html.escape, and links are only allowed to be
http(s), so catalogue or LLM text can never inject markup into the page.
"""
from __future__ import annotations

import html

from .config import TOPIC_LABELS, TOPICS

TOPIC_COLORS = {
    "python": "#2563eb", "data": "#0891b2", "prompting": "#9333ea",
    "ml": "#ea580c", "evaluation": "#16a34a", "ethics": "#db2777",
}
TOPIC_ICONS = {
    "python": "🐍", "data": "📊", "prompting": "💬",
    "ml": "🤖", "evaluation": "🎯", "ethics": "⚖️",
}
LEVELS = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}

APP_CSS = """
<style>
.block-container { padding-top: 2.2rem; max-width: 1150px; }
.hero { padding: 1.5rem 1.8rem; border-radius: 18px; color: #fff; margin-bottom: 1rem;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 55%, #EC4899 100%); }
.hero h1 { margin: 0; font-size: 2.05rem; color: #fff; padding: 0; }
.hero p { margin: .35rem 0 0; font-size: 1.02rem; opacity: .93; }
.stepper { display: flex; gap: .6rem; margin: .2rem 0 1.3rem; }
.step { flex: 1; padding: .55rem .9rem; border-radius: 12px; font-size: .9rem;
        border: 1px solid rgba(128,128,128,.30); opacity: .6; }
.step.active { opacity: 1; border-color: #4F46E5; background: rgba(79,70,229,.12); font-weight: 600; }
.step.done { opacity: 1; border-color: #16a34a; background: rgba(22,163,74,.10); }
.kpi { border: 1px solid rgba(128,128,128,.28); border-radius: 14px; padding: .85rem 1rem; height: 100%; }
.kpi .label { font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; opacity: .7; }
.kpi .value { font-size: 1.45rem; font-weight: 700; line-height: 1.25; margin-top: .15rem; }
.kpi .sub { font-size: .82rem; opacity: .7; margin-top: .1rem; }
.skill { margin-bottom: .6rem; }
.skill-top { display: flex; justify-content: space-between; font-size: .88rem; margin-bottom: .2rem; }
.track { height: 9px; border-radius: 99px; background: rgba(128,128,128,.22); overflow: hidden; }
.fill { height: 100%; border-radius: 99px; }
.badge { display: inline-block; padding: .12rem .6rem; border-radius: 999px; font-size: .74rem;
         font-weight: 600; margin: 0 .35rem .3rem 0; }
.badge.plain { background: rgba(128,128,128,.18); }
.rcard { border: 1px solid rgba(128,128,128,.28); border-left: 6px solid var(--c); border-radius: 14px;
         padding: .85rem 1.1rem; margin-bottom: .75rem; }
.rcard .top { display: flex; align-items: baseline; gap: .6rem; }
.rcard .num { font-weight: 800; font-size: 1.15rem; color: var(--c); }
.rcard .title { font-weight: 650; font-size: 1.03rem; }
.rcard .prov { opacity: .7; font-size: .85rem; margin: .1rem 0 .4rem; }
.rcard .why { font-size: .9rem; opacity: .9; margin: .25rem 0 .45rem; }
.rcard a { font-size: .88rem; font-weight: 600; text-decoration: none; }
.typebox { border-radius: 14px; padding: 1rem 1.2rem; background: rgba(79,70,229,.10);
           border: 1px solid rgba(79,70,229,.35); }
.typebox .name { font-weight: 700; font-size: 1.1rem; margin-bottom: .3rem; }
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
        return (f'<span class="badge" style="background:{color}22;color:{color};'
                f'border:1px solid {color}55">{esc(text)}</span>')
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
