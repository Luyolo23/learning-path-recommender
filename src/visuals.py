"""Matplotlib figures (built with Figure, not pyplot, so they are safe inside Streamlit)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .clustering import ClusterModel, skills_to_vector
from .config import TOPIC_LABELS, TOPICS

ACCENT = "#4F46E5"
SHORT_LABELS = {
    "python": "Python", "data": "Data", "prompting": "Prompting",
    "ml": "ML basics", "evaluation": "Evaluation", "ethics": "Resp. AI",
}


def radar_chart(skills: dict[str, float]) -> Figure:
    """Spider chart of the six skill scores."""
    values = [skills[t] for t in TOPICS]
    angles = np.linspace(0, 2 * np.pi, len(TOPICS), endpoint=False).tolist()
    values_c, angles_c = values + values[:1], angles + angles[:1]

    fig = Figure(figsize=(4.6, 4.6))
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles_c, values_c, color=ACCENT, linewidth=2)
    ax.fill(angles_c, values_c, color=ACCENT, alpha=0.25)
    ax.set_xticks(angles)
    ax.set_xticklabels([SHORT_LABELS[t] for t in TOPICS], fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25%", "50%", "75%", "100%"], fontsize=7, color="grey")
    ax.set_title("Your skill profile", fontsize=11, pad=14)
    fig.tight_layout()
    return fig


def cluster_scatter(model: ClusterModel, students: pd.DataFrame, skills: dict[str, float] | None = None,
                    title: str = "Learner archetypes (PCA view of synthetic learners)") -> Figure:
    """2-D PCA scatter coloured by cluster, with the current student as a star."""
    X = students[TOPICS].to_numpy(dtype=float)
    pts = model.pca.transform(X)
    centers = model.pca.transform(model.kmeans.cluster_centers_)

    fig = Figure(figsize=(7.5, 6.4))
    ax = fig.add_subplot(111)
    for c in range(model.k):
        mask = model.labels == c
        ax.scatter(pts[mask, 0], pts[mask, 1], s=18, alpha=0.6, label=f"{c}: {model.profiles[c].name}")
        ax.annotate(str(c), centers[c], fontsize=11, fontweight="bold", ha="center", va="center",
                    bbox=dict(boxstyle="circle,pad=0.2", fc="white", ec="black", lw=0.8))
    if skills is not None:
        me = model.pca.transform(skills_to_vector(skills).reshape(1, -1))
        ax.scatter(me[:, 0], me[:, 1], marker="*", s=420, c="gold", edgecolors="black", zorder=5, label="You")
    ax.set_xlabel("Principal component 1")
    ax.set_ylabel("Principal component 2")
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=1, frameon=False)
    fig.tight_layout()
    return fig


def k_selection_chart(k_scores: pd.DataFrame, chosen_k: int) -> Figure:
    """Elbow (inertia) and silhouette side by side."""
    fig = Figure(figsize=(8, 3.4))
    ax1, ax2 = fig.subplots(1, 2)
    ax1.plot(k_scores["k"], k_scores["inertia"], marker="o", color=ACCENT)
    ax1.set_title("Elbow method (inertia)", fontsize=10)
    ax1.set_xlabel("k")
    ax1.set_ylabel("Inertia")
    ax2.plot(k_scores["k"], k_scores["silhouette"], marker="o", color="#059669")
    ax2.axvline(chosen_k, linestyle="--", color="grey")
    ax2.set_title(f"Silhouette score (chosen k = {chosen_k})", fontsize=10)
    ax2.set_xlabel("k")
    ax2.set_ylabel("Silhouette")
    fig.tight_layout()
    return fig
