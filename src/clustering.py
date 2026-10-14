"""Unsupervised learning: group learners into archetypes with K-Means.

Pipeline
--------
1. `evaluate_k_range` tries several values of k and records inertia + silhouette.
2. `train_cluster_model` picks the k with the best silhouette (unless you force k),
   fits K-Means and a 2-D PCA projection (for plotting).
3. `describe_cluster` turns each centroid into a human-readable archetype name,
   a learning "focus" and pacing advice.
4. `assign_cluster` places a new student into the nearest cluster.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from .config import RANDOM_SEED, TOPIC_LABELS, TOPICS

FOCUS_ADVICE = {
    "beginner": (
        "You are at the start of your journey, which is a great place to be. "
        "Choose short, beginner-friendly resources and build a daily habit: "
        "30-45 minutes a day beats one long weekend session. Prefer interactive "
        "exercises over long lectures."
    ),
    "practice_led": (
        "You learn by doing and your hands-on skills are ahead of your theory. "
        "Keep that momentum, but schedule explicit time for ML concepts and "
        "evaluation so your projects rest on solid foundations."
    ),
    "theory_led": (
        "Your concepts are ahead of your coding. Turn them into code: pair every "
        "theory resource with a small exercise or mini project so the ideas stick."
    ),
    "balanced": (
        "You have a solid all-round base. Go deeper on your weakest topic and "
        "start a portfolio project that combines several skills."
    ),
    "mixed": (
        "Your profile is uneven in an interesting way. Follow the path in order, "
        "and revisit your weakest topic with one practice exercise every week."
    ),
}


@dataclass
class ClusterProfile:
    name: str
    focus: str
    advice: str
    centroid: list[float]


@dataclass
class ClusterModel:
    kmeans: KMeans
    pca: PCA
    k: int
    silhouette: float
    k_scores: pd.DataFrame
    profiles: dict[int, ClusterProfile] = field(default_factory=dict)
    labels: np.ndarray | None = None


def evaluate_k_range(X: np.ndarray, k_range=range(3, 8), seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Fit K-Means for each k and return inertia and silhouette scores."""
    rows = []
    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X)
        rows.append({
            "k": k,
            "inertia": float(km.inertia_),
            "silhouette": float(silhouette_score(X, km.labels_)),
        })
    return pd.DataFrame(rows)


def describe_cluster(centroid: np.ndarray) -> ClusterProfile:
    """Turn a centroid (mean skill per topic) into a name, focus and advice."""
    c = np.asarray(centroid, dtype=float)
    idx = {t: i for i, t in enumerate(TOPICS)}
    mean = c.mean()
    spread = c.max() - c.min()
    code = np.mean([c[idx["python"]], c[idx["data"]]])
    theory = np.mean([c[idx["ml"]], c[idx["evaluation"]], c[idx["ethics"]]])

    top = TOPICS[int(c.argmax())]
    bottom = TOPICS[int(c.argmin())]

    if mean < 0.35:
        name, focus = "Foundations builder", "beginner"
    elif spread < 0.2 and mean >= 0.55:
        name, focus = "Well-rounded intermediate", "balanced"
    else:
        name = f"Strong in {TOPIC_LABELS[top]}, growing in {TOPIC_LABELS[bottom]}"
        if code - theory > 0.2:
            focus = "practice_led"
        elif theory - code > 0.2:
            focus = "theory_led"
        else:
            focus = "mixed"

    return ClusterProfile(name=name, focus=focus, advice=FOCUS_ADVICE[focus],
                          centroid=[round(float(v), 3) for v in c])


def train_cluster_model(students: pd.DataFrame, k: int | None = None,
                        k_range=range(3, 8), seed: int = RANDOM_SEED) -> ClusterModel:
    """Fit K-Means (choosing k by silhouette unless `k` is given) and a PCA for plotting."""
    X = students[TOPICS].to_numpy(dtype=float)
    k_scores = evaluate_k_range(X, k_range, seed)
    if k is None:
        k = int(k_scores.loc[k_scores["silhouette"].idxmax(), "k"])

    km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X)
    pca = PCA(n_components=2, random_state=seed).fit(X)

    profiles = {i: describe_cluster(c) for i, c in enumerate(km.cluster_centers_)}
    # Make names unique if two centroids produce the same label.
    seen: dict[str, int] = {}
    for i in sorted(profiles):
        base = profiles[i].name
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            profiles[i].name = f"{base} ({seen[base]})"

    return ClusterModel(
        kmeans=km, pca=pca, k=k,
        silhouette=float(silhouette_score(X, km.labels_)),
        k_scores=k_scores, profiles=profiles, labels=km.labels_,
    )


def skills_to_vector(skills: dict[str, float]) -> np.ndarray:
    return np.array([skills[t] for t in TOPICS], dtype=float)


def assign_cluster(model: ClusterModel, skills: dict[str, float]) -> tuple[int, ClusterProfile]:
    """Return (cluster id, profile) for a student's skill dict."""
    vec = skills_to_vector(skills).reshape(1, -1)
    cluster_id = int(model.kmeans.predict(vec)[0])
    return cluster_id, model.profiles[cluster_id]
