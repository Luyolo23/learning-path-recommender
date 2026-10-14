"""Turn a ranked learning path into a 4-week study plan.

Two layers, deliberately separated:

1. STRUCTURE (always deterministic): `schedule_resources` assigns each recommended
   resource to a week so the weekly hours budget is respected.
2. WORDING (optional, LLM): the model only writes a summary, a weekly goal, a tip,
   and a one-line "why" per resource. It never chooses or invents resources.
   Its JSON reply is validated; anything invalid (unknown ids, links, wrong
   shape, too long) is discarded and replaced by the rule-based text.

If there is no API key, the `groq` package is missing, or the call fails, the
app falls back to the rule-based plan, so it always works offline.
"""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy

import pandas as pd

from .clustering import ClusterProfile
from .config import PLAN_WEEKS, TOPIC_LABELS, TOPIC_ORDER

# Model names change over time. Check https://console.groq.com/docs/models and
# override with GROQ_MODEL in your .env file if this one is retired.
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

WEEKLY_TIPS = [
    "Start small: finish one resource completely before opening the next.",
    "Practise while you learn: code along or note down one thing you could build with it.",
    "Review what you learned last week for 10 minutes before starting something new.",
    "Write a short summary of what you learned. Teaching it in your own words locks it in.",
]


# --------------------------------------------------------------------------- #
# 1. Deterministic structure
# --------------------------------------------------------------------------- #
def schedule_resources(rec: pd.DataFrame, hours_per_week: float,
                       weeks: int = PLAN_WEEKS) -> tuple[dict[int, list[str]], list[str]]:
    """Greedy week-by-week fill. Returns ({week: [resource ids]}, stretch ids).

    A resource longer than the weekly budget gets a week to itself.
    Anything that does not fit in `weeks` weeks goes to the 'stretch' list.
    """
    schedule: dict[int, list[str]] = {w: [] for w in range(1, weeks + 1)}
    stretch: list[str] = []
    week, used = 1, 0.0
    for _, r in rec.iterrows():
        hours = float(r["hours"])
        if week > weeks:
            stretch.append(r["id"])
            continue
        if schedule[week] and used + hours > hours_per_week:
            week += 1
            used = 0.0
            if week > weeks:
                stretch.append(r["id"])
                continue
        schedule[week].append(r["id"])
        used += hours
    return schedule, stretch


def _item(row) -> dict:
    return {
        "id": row["id"], "title": row["title"], "provider": row["provider"],
        "topic": row["topic"], "hours": float(row["hours"]), "url": row["url"],
        "why": row["reason"],
    }


def build_rule_based_plan(rec: pd.DataFrame, schedule: dict[int, list[str]], stretch: list[str],
                          profile: ClusterProfile, skills: dict[str, float]) -> dict:
    """Plan text written by simple rules (no LLM)."""
    by_id = {r["id"]: r for _, r in rec.iterrows()}
    weakest = sorted(skills, key=skills.get)[:2]
    weak_names = " and ".join(TOPIC_LABELS[t] for t in weakest)

    weeks = []
    for w, ids in schedule.items():
        if not ids:
            continue
        topics = []
        for i in ids:
            t = by_id[i]["topic"]
            if t not in topics:
                topics.append(t)
        topics.sort(key=TOPIC_ORDER.index)
        weeks.append({
            "week": w,
            "goal": "Focus on " + " and ".join(TOPIC_LABELS[t] for t in topics) + ".",
            "tip": WEEKLY_TIPS[(w - 1) % len(WEEKLY_TIPS)],
            "items": [_item(by_id[i]) for i in ids],
        })

    return {
        "source": "rule-based",
        "summary": (f"Your learner type is '{profile.name}'. Your biggest gaps are {weak_names}, "
                    f"so this path starts with the foundations and builds up from there."),
        "weeks": weeks,
        "stretch": [_item(by_id[i]) for i in stretch],
    }


# --------------------------------------------------------------------------- #
# 2. Optional LLM wording (Groq) with validation
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "You are a supportive learning coach. You will receive a student's skill scores and a "
    "FIXED weekly schedule of resources chosen by a recommender system. Your job is only to "
    "write short, encouraging text for that schedule.\n"
    "Rules:\n"
    "- Do NOT add, remove, rename or reorder resources. Refer to them only by their id.\n"
    "- Do NOT include any URLs or links.\n"
    "- Keep every text field under 200 characters.\n"
    "- Be specific, warm and practical. Do not give medical, legal or financial advice.\n"
    "- Reply with a single JSON object and nothing else."
)


def build_messages(plan: dict, profile: ClusterProfile, skills: dict[str, float],
                   hours_per_week: float, goal: str) -> list[dict]:
    payload = {
        "learner_type": profile.name,
        "skill_scores_0_to_1": {TOPIC_LABELS[t]: round(v, 2) for t, v in skills.items()},
        "hours_per_week": hours_per_week,
        "learner_goal": goal.strip()[:300] if goal else "",
        "schedule": [
            {"week": wk["week"],
             "resources": [{"id": it["id"], "title": it["title"], "topic": TOPIC_LABELS[it["topic"]],
                            "hours": it["hours"]} for it in wk["items"]]}
            for wk in plan["weeks"]
        ],
    }
    schema = {
        "summary": "2 sentences max about this learner's path",
        "weeks": [{"week": 1, "goal": "one sentence", "tip": "one practical tip",
                   "why": {"<resource id>": "one sentence on why it helps THIS learner"}}],
    }
    user = ("Student data:\n" + json.dumps(payload, indent=2)
            + "\n\nReturn JSON in exactly this shape:\n" + json.dumps(schema, indent=2))
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def _call_groq(messages: list[dict], api_key: str, model: str) -> str:
    from groq import Groq  # imported lazily so the app works without the package

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model, messages=messages, temperature=0.4, max_tokens=1500,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


_LINK = re.compile(r"https?://|www\.", re.IGNORECASE)


def _clean_text(value, max_len: int):
    """Return the string if it is safe to show, else None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > max_len or _LINK.search(value):
        return None
    return value


def merge_llm_text(plan: dict, raw: str) -> tuple[dict, int]:
    """Validate the LLM JSON and copy ONLY safe text fields into a copy of `plan`.

    Returns (new_plan, number_of_rejected_fields). Raises ValueError if the reply
    is not usable JSON at all.
    """
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("The AI reply was not valid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("The AI reply had an unexpected shape")

    new_plan = deepcopy(plan)
    rejected = 0

    summary = _clean_text(data.get("summary"), 500)
    if summary:
        new_plan["summary"] = summary
    else:
        rejected += 1

    llm_weeks = data.get("weeks")
    if not isinstance(llm_weeks, list):
        raise ValueError("The AI reply had no 'weeks' list")

    by_week = {wk["week"]: wk for wk in new_plan["weeks"]}
    for entry in llm_weeks:
        if not isinstance(entry, dict) or entry.get("week") not in by_week:
            rejected += 1
            continue
        wk = by_week[entry["week"]]
        for field in ("goal", "tip"):
            text = _clean_text(entry.get(field), 250)
            if text:
                wk[field] = text
            else:
                rejected += 1
        why = entry.get("why")
        if isinstance(why, dict):
            valid_ids = {it["id"]: it for it in wk["items"]}
            for rid, text in why.items():
                clean = _clean_text(text, 250)
                if rid in valid_ids and clean:
                    valid_ids[rid]["why"] = clean
                else:
                    rejected += 1  # unknown id (possible invented resource) or unsafe text
    return new_plan, rejected


def generate_plan(rec: pd.DataFrame, profile: ClusterProfile, skills: dict[str, float],
                  hours_per_week: float, goal: str = "", use_llm: bool = False,
                  api_key: str | None = None, model: str | None = None,
                  caller=None) -> tuple[dict, str | None]:
    """Build the plan. Returns (plan, optional notice to show the user).

    `caller` lets tests inject a fake LLM: caller(messages, api_key, model) -> str.
    """
    schedule, stretch = schedule_resources(rec, hours_per_week)
    plan = build_rule_based_plan(rec, schedule, stretch, profile, skills)
    if not use_llm:
        return plan, None
    if not api_key:
        return plan, "AI wording is switched on but no Groq API key was provided, so the built-in plan is shown."

    model = model or os.getenv("GROQ_MODEL") or DEFAULT_GROQ_MODEL
    try:
        raw = (caller or _call_groq)(build_messages(plan, profile, skills, hours_per_week, goal),
                                     api_key, model)
        merged, rejected = merge_llm_text(plan, raw)
        merged["source"] = "ai-worded"
        notice = None
        if rejected:
            notice = (f"The AI's wording was checked automatically and {rejected} unsafe or invalid "
                      f"field(s) were replaced with the built-in text.")
        return merged, notice
    except ImportError:
        return plan, "The 'groq' package is not installed (run: pip install -r requirements.txt). Showing the built-in plan."
    except Exception as exc:  # never show raw error text: it could contain secrets
        return plan, f"AI wording was unavailable ({type(exc).__name__}). Showing the built-in plan."


def plan_to_markdown(plan: dict, profile_name: str) -> str:
    """Export the plan as Markdown (used by the download button)."""
    lines = [f"# My 4-week learning plan", "", f"**Learner type:** {profile_name}", "", plan["summary"], ""]
    for wk in plan["weeks"]:
        total = sum(it["hours"] for it in wk["items"])
        lines += [f"## Week {wk['week']} (about {total:g} h)", wk["goal"], ""]
        for it in wk["items"]:
            lines.append(f"- [{it['title']}]({it['url']}) - {it['provider']}, {it['hours']:g} h. {it['why']}")
        lines += ["", f"*Tip: {wk['tip']}*", ""]
    if plan["stretch"]:
        lines += ["## If you have extra time", ""]
        for it in plan["stretch"]:
            lines.append(f"- [{it['title']}]({it['url']}) - {it['provider']}, {it['hours']:g} h")
    return "\n".join(lines) + "\n"
