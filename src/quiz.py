"""Diagnostic quiz: load questions and turn answers into a skill vector."""
from __future__ import annotations

import json
from collections import defaultdict

from .config import QUIZ_PATH, TOPICS

REQUIRED_KEYS = ("id", "topic", "question", "options", "answer", "explanation")


def load_questions(path=QUIZ_PATH) -> list[dict]:
    """Load and validate the quiz question bank."""
    with open(path, encoding="utf-8") as f:
        questions = json.load(f)

    seen_ids = set()
    topics_seen = set()
    for q in questions:
        missing = [k for k in REQUIRED_KEYS if k not in q]
        if missing:
            raise ValueError(f"Question {q.get('id')} is missing keys: {missing}")
        if q["id"] in seen_ids:
            raise ValueError(f"Duplicate question id: {q['id']}")
        if q["topic"] not in TOPICS:
            raise ValueError(f"Question {q['id']} has unknown topic '{q['topic']}'")
        if not 0 <= q["answer"] < len(q["options"]):
            raise ValueError(f"Question {q['id']}: 'answer' index out of range")
        seen_ids.add(q["id"])
        topics_seen.add(q["topic"])

    uncovered = set(TOPICS) - topics_seen
    if uncovered:
        raise ValueError(f"No quiz questions for topics: {sorted(uncovered)}")
    return questions


def score_answers(answers: dict[str, int], questions: list[dict]) -> dict[str, float]:
    """Return {topic: score between 0 and 1}.

    `answers` maps question id -> chosen option index. Unanswered questions
    count as incorrect.
    """
    correct: dict[str, int] = defaultdict(int)
    total: dict[str, int] = defaultdict(int)
    for q in questions:
        total[q["topic"]] += 1
        if answers.get(q["id"]) == q["answer"]:
            correct[q["topic"]] += 1
    return {t: correct[t] / total[t] for t in TOPICS if total[t]}
