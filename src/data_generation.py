"""Synthetic learner data.

There is no public dataset of "quiz skill vectors", so we generate one from a
handful of deliberately designed learner archetypes plus noise. The
`true_archetype` column is ONLY used to sanity-check the clustering (see
scripts/evaluate.py); it is never given to the model.

IMPORTANT: say clearly in your README/portfolio that this data is synthetic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RANDOM_SEED, STUDENTS_PATH, TOPICS

# name -> (mean skill per topic in TOPICS order, share of the population)
#          python data  prompt ml   eval  ethics
ARCHETYPES = {
    "Beginner across the board": ([0.20, 0.20, 0.25, 0.15, 0.10, 0.25], 0.25),
    "Practical coder, light on theory": ([0.80, 0.75, 0.60, 0.30, 0.25, 0.30], 0.20),
    "Theory-strong, new to code": ([0.35, 0.30, 0.50, 0.75, 0.70, 0.70], 0.20),
    "Prompt-savvy, code-light": ([0.30, 0.35, 0.85, 0.30, 0.25, 0.55], 0.15),
    "Well-rounded intermediate": ([0.70, 0.70, 0.70, 0.65, 0.65, 0.60], 0.20),
}


def generate_students(n: int = 300, seed: int = RANDOM_SEED, noise: float = 0.10) -> pd.DataFrame:
    """Create `n` synthetic learners (rows) with a skill score per topic (columns)."""
    rng = np.random.default_rng(seed)
    names = list(ARCHETYPES)
    shares = np.array([ARCHETYPES[name][1] for name in names], dtype=float)
    shares /= shares.sum()

    picks = rng.choice(len(names), size=n, p=shares)
    means = np.array([ARCHETYPES[names[i]][0] for i in picks], dtype=float)
    skills = np.clip(means + rng.normal(0.0, noise, size=means.shape), 0.0, 1.0)

    df = pd.DataFrame(skills.round(3), columns=TOPICS)
    df["true_archetype"] = [names[i] for i in picks]
    return df


def load_or_generate_students() -> pd.DataFrame:
    """Use data/synthetic_students.csv if present, otherwise generate in memory."""
    if STUDENTS_PATH.exists():
        return pd.read_csv(STUDENTS_PATH)
    return generate_students()
