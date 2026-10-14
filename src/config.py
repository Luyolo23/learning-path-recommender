"""Central configuration: paths, topics, and tuning constants.

Everything you might want to tweak (topics, weights, thresholds) lives here so
the rest of the code stays free of "magic numbers".
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
RESOURCES_PATH = DATA_DIR / "resources.csv"
QUIZ_PATH = DATA_DIR / "quiz_questions.json"
STUDENTS_PATH = DATA_DIR / "synthetic_students.csv"

RANDOM_SEED = 42

# --------------------------------------------------------------------------- #
# Topics (the "skill vector" always follows this order)
# --------------------------------------------------------------------------- #
TOPICS = ["python", "data", "prompting", "ml", "evaluation", "ethics"]

TOPIC_LABELS = {
    "python": "Python Programming",
    "data": "Data Handling & Visualisation",
    "prompting": "Prompt Engineering",
    "ml": "Machine Learning Fundamentals",
    "evaluation": "Model Evaluation",
    "ethics": "Responsible AI",
}

# Topic -> topics that should be reasonably solid first.
PREREQUISITES = {
    "data": ["python"],
    "ml": ["python", "data"],
    "evaluation": ["ml"],
}

# Order in which topics appear in a learning path (respects PREREQUISITES).
TOPIC_ORDER = ["python", "data", "prompting", "ml", "evaluation", "ethics"]

# A prerequisite counts as "weak" below this skill score (0-1).
WEAK_THRESHOLD = 0.4

# --------------------------------------------------------------------------- #
# Recommender tuning
# --------------------------------------------------------------------------- #
SECONDARY_TOPIC_WEIGHT = 0.2      # weight of a resource's secondary topic
SCORE_WEIGHTS = {                 # must add up to 1.0
    "gap_alignment": 0.5,         # cosine(gap vector, resource topic vector)
    "primary_gap": 0.3,           # how big the gap is in the resource's main topic
    "difficulty_fit": 0.2,        # does the resource level match the student?
}
GOAL_BOOST = 0.2                  # extra weight for free-text goal similarity
PREREQUISITE_PENALTY = 0.6        # multiplier: level 2-3 resource while a prerequisite is weak
LIGHT_PREREQUISITE_PENALTY = 0.85 # multiplier: level 1 resource while a prerequisite is weak
FOUNDATION_BOOST = 1.25           # multiplier: weak topic that blocks other weak topics
LONG_RESOURCE_SHARE = 0.5         # resource > 50% of the whole time budget is "long"
LONG_RESOURCE_PENALTY = 0.75      # multiplier for long resources
TOO_LONG_PENALTY = 0.4            # multiplier for resources longer than the whole budget
MIN_GAP = 0.15                    # ignore topics where the student scored > 85%
DEFAULT_N_RECOMMENDATIONS = 8
MAX_PER_TOPIC = 3
PLAN_WEEKS = 4

# --------------------------------------------------------------------------- #
# Demo profiles (skip the quiz while demoing / testing)
# --------------------------------------------------------------------------- #
DEMO_PROFILES = {
    "Beginner across the board": dict(
        python=0.33, data=0.0, prompting=0.33, ml=0.0, evaluation=0.0, ethics=0.33),
    "Practical coder, light on theory": dict(
        python=1.0, data=0.67, prompting=0.67, ml=0.33, evaluation=0.0, ethics=0.33),
    "Theory-strong, new to code": dict(
        python=0.33, data=0.33, prompting=0.67, ml=1.0, evaluation=0.67, ethics=0.67),
    "Prompt-savvy, code-light": dict(
        python=0.33, data=0.33, prompting=1.0, ml=0.33, evaluation=0.0, ethics=0.67),
    "Well-rounded intermediate": dict(
        python=0.67, data=0.67, prompting=0.67, ml=0.67, evaluation=0.67, ethics=0.67),
}
