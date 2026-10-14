"""Content-based recommender with prerequisite-aware ordering.

How a resource is scored for a student
--------------------------------------
gap vector      = 1 - skill (per topic)
resource vector = 1.0 on its primary topic, 0.2 on its secondary topic

    base  = 0.5 * cosine(gap, resource)        how well the resource matches ALL gaps
          + 0.3 * gap in the primary topic     how big the main gap is
          + 0.2 * difficulty fit               resource level vs. student level
    score = base * prerequisite penalty        (if a prerequisite topic is weak)
               * foundation boost              (if this weak topic blocks other weak topics)
               * time-budget penalty           (if the resource is very long for the weekly hours)
          + 0.2 * goal similarity              (TF-IDF, only if a goal was typed)

The top N are picked (max 3 per topic) and then ORDERED by topic prerequisites
(Python -> Data -> Prompting -> ML -> Evaluation -> Responsible AI), easiest first.
The recommender never calls an LLM: every pick is explainable.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import (DEFAULT_N_RECOMMENDATIONS, FOUNDATION_BOOST, GOAL_BOOST,
                     LIGHT_PREREQUISITE_PENALTY, LONG_RESOURCE_PENALTY, LONG_RESOURCE_SHARE,
                     MAX_PER_TOPIC, MIN_GAP, PLAN_WEEKS, PREREQUISITE_PENALTY, PREREQUISITES,
                     RESOURCES_PATH, SCORE_WEIGHTS, SECONDARY_TOPIC_WEIGHT, TOO_LONG_PENALTY,
                     TOPIC_LABELS, TOPIC_ORDER, TOPICS, WEAK_THRESHOLD)

REQUIRED_COLUMNS = ["id", "title", "provider", "topic", "secondary_topic", "difficulty",
                    "format", "hours", "url", "description"]


def load_resources(path=RESOURCES_PATH) -> pd.DataFrame:
    """Load and validate the resource catalogue."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"resources.csv is missing columns: {missing}")
    df["secondary_topic"] = df["secondary_topic"].fillna("").astype(str)
    if df["id"].duplicated().any():
        raise ValueError("resources.csv has duplicate ids")
    bad_topics = set(df["topic"]) - set(TOPICS)
    bad_secondary = set(df["secondary_topic"]) - set(TOPICS) - {""}
    if bad_topics or bad_secondary:
        raise ValueError(f"Unknown topics in resources.csv: {sorted(bad_topics | bad_secondary)}")
    if not df["difficulty"].between(1, 3).all():
        raise ValueError("difficulty must be 1, 2 or 3")
    if (df["hours"] <= 0).any():
        raise ValueError("hours must be positive")
    return df.reset_index(drop=True)


def _topic_vector(topic: str, secondary: str) -> np.ndarray:
    v = np.zeros(len(TOPICS))
    v[TOPICS.index(topic)] = 1.0
    if secondary:
        v[TOPICS.index(secondary)] = SECONDARY_TOPIC_WEIGHT
    return v


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(a @ b / denom) if denom else 0.0


def target_difficulty(skill: float) -> int:
    """Map a 0-1 skill score to the resource level (1-3) that suits the student."""
    if skill < 0.4:
        return 1
    if skill < 0.75:
        return 2
    return 3


def _goal_similarity(resources: pd.DataFrame, goal_text: str) -> np.ndarray:
    """TF-IDF cosine similarity between the typed goal and each resource."""
    if not goal_text or not goal_text.strip():
        return np.zeros(len(resources))
    corpus = (resources["title"] + " " + resources["description"] + " "
              + resources["topic"].map(TOPIC_LABELS)).tolist()
    try:
        vec = TfidfVectorizer(stop_words="english")
        matrix = vec.fit_transform(corpus)
        goal_vec = vec.transform([goal_text])
        return cosine_similarity(goal_vec, matrix).ravel()
    except ValueError:  # e.g. goal made only of stop-words
        return np.zeros(len(resources))


def _blocking_topics(skills: dict[str, float]) -> dict[str, list[str]]:
    """Weak topics that are prerequisites of other topics the student still needs.

    Returns {weak_prerequisite: [dependent topics it unlocks]}.
    """
    blocking: dict[str, list[str]] = {}
    for dependent, prereqs in PREREQUISITES.items():
        if 1.0 - skills[dependent] < MIN_GAP:
            continue  # the dependent topic is already strong, nothing to unlock
        for p in prereqs:
            if skills[p] < WEAK_THRESHOLD:
                blocking.setdefault(p, []).append(dependent)
    return blocking


def _time_factor(hours: float, hours_per_week: float | None) -> float:
    if not hours_per_week:
        return 1.0
    budget = hours_per_week * PLAN_WEEKS
    if hours > budget:
        return TOO_LONG_PENALTY
    if hours > LONG_RESOURCE_SHARE * budget:
        return LONG_RESOURCE_PENALTY
    return 1.0


def _reason(row, skills, weak_prereqs, unlocks, goal_sim, stretch, time_factor) -> str:
    topic = row["topic"]
    label = TOPIC_LABELS[topic]
    level = {1: "beginner", 2: "intermediate", 3: "advanced"}[int(row["difficulty"])]
    if stretch:
        text = f"Stretch goal in {label}: you already scored {skills[topic]:.0%}, so this is {level}-level depth."
    else:
        text = f"Targets your {label} gap (you scored {skills[topic]:.0%}); {level} level fits you."
    if unlocks:
        names = ", ".join(TOPIC_LABELS[u] for u in unlocks)
        text += f" Foundation first: it unlocks {names}."
    if weak_prereqs:
        names = ", ".join(TOPIC_LABELS[p] for p in weak_prereqs)
        text += f" Comes after your {names} basics."
    if goal_sim >= 0.15:
        text += " Matches the goal you typed."
    if time_factor < 1.0:
        text += f" Note: long ({row['hours']:g} h), so it may take more than the 4 weeks."
    return text


def recommend(skills: dict[str, float], resources: pd.DataFrame, n: int = DEFAULT_N_RECOMMENDATIONS,
              goal_text: str = "", hours_per_week: float | None = None,
              max_per_topic: int = MAX_PER_TOPIC, min_gap: float = MIN_GAP,
              _stretch: bool = False) -> pd.DataFrame:
    """Return an ordered learning path (DataFrame) with a score and a reason per resource."""
    missing = [t for t in TOPICS if t not in skills]
    if missing:
        raise ValueError(f"skills is missing topics: {missing}")

    skill_vec = np.array([skills[t] for t in TOPICS], dtype=float)
    gap_vec = 1.0 - skill_vec
    goal_sims = _goal_similarity(resources, goal_text)
    blocking = _blocking_topics(skills)
    w = SCORE_WEIGHTS

    rows = []
    for i, r in resources.iterrows():
        topic = r["topic"]
        rv = _topic_vector(topic, r["secondary_topic"])
        primary_skill = skills[topic]
        primary_gap = 1.0 - primary_skill
        fit = 1.0 - abs(int(r["difficulty"]) - target_difficulty(primary_skill)) / 2.0

        score = (w["gap_alignment"] * _cosine(gap_vec, rv)
                 + w["primary_gap"] * primary_gap
                 + w["difficulty_fit"] * fit)

        weak_prereqs = [p for p in PREREQUISITES.get(topic, []) if skills[p] < WEAK_THRESHOLD]
        if weak_prereqs:
            score *= PREREQUISITE_PENALTY if int(r["difficulty"]) >= 2 else LIGHT_PREREQUISITE_PENALTY
        unlocks = blocking.get(topic, [])
        if unlocks:
            score *= FOUNDATION_BOOST
        tf = _time_factor(float(r["hours"]), hours_per_week)
        score *= tf
        score += GOAL_BOOST * goal_sims[i]

        rows.append((i, score, primary_gap, weak_prereqs, unlocks, goal_sims[i], tf))

    rows.sort(key=lambda x: x[1], reverse=True)

    picked, per_topic = [], Counter()
    for i, score, primary_gap, weak_prereqs, unlocks, gsim, tf in rows:
        r = resources.loc[i]
        if primary_gap < min_gap:
            continue
        if per_topic[r["topic"]] >= max_per_topic:
            continue
        item = r.to_dict()
        item["score"] = round(float(score), 4)
        item["reason"] = _reason(r, skills, weak_prereqs, unlocks, gsim, _stretch, tf)
        picked.append(item)
        per_topic[r["topic"]] += 1
        if len(picked) == n:
            break

    if not picked and min_gap > 0:
        # Student scored very high everywhere: offer advanced "stretch" material instead.
        return recommend(skills, resources, n=n, goal_text=goal_text, hours_per_week=hours_per_week,
                         max_per_topic=max_per_topic, min_gap=0.0, _stretch=True)

    out = pd.DataFrame(picked)
    if out.empty:
        return out
    out["_order"] = out["topic"].map(TOPIC_ORDER.index)
    out = out.sort_values(["_order", "difficulty", "score"], ascending=[True, True, False])
    out = out.drop(columns="_order").reset_index(drop=True)
    out.insert(0, "order", range(1, len(out) + 1))
    return out
