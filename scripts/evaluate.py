"""Evaluate the clustering and the recommender and save results to outputs/.

    python scripts/evaluate.py

Creates:
  outputs/k_selection.png         elbow + silhouette plot
  outputs/clusters_pca.png        PCA scatter of the learner clusters
  outputs/evaluation_report.md    tables you can paste into your README/portfolio
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.metrics import adjusted_rand_score  # noqa: E402

from src.clustering import assign_cluster, train_cluster_model  # noqa: E402
from src.config import DEMO_PROFILES, OUTPUT_DIR, TOPIC_LABELS, TOPICS  # noqa: E402
from src.data_generation import load_or_generate_students  # noqa: E402
from src.recommender import load_resources, recommend  # noqa: E402
from src.visuals import cluster_scatter, k_selection_chart  # noqa: E402

# Extra hand-made profiles: (name, skills, topic we expect to appear in the path)
EXTRA_PROFILES = [
    ("Strong Python, no ML", dict(python=1.0, data=0.67, prompting=0.67, ml=0.0, evaluation=0.0, ethics=0.67), "ml"),
    ("No coding, strong prompting", dict(python=0.0, data=0.0, prompting=1.0, ml=0.33, evaluation=0.0, ethics=0.33), "python"),
    ("Strong everywhere except ethics", dict(python=1.0, data=1.0, prompting=1.0, ml=1.0, evaluation=1.0, ethics=0.0), "ethics"),
]


def md_table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    students = load_or_generate_students()
    model = train_cluster_model(students)
    ari = adjusted_rand_score(students["true_archetype"], model.labels)

    k_selection_chart(model.k_scores, model.k).savefig(OUTPUT_DIR / "k_selection.png", dpi=150, bbox_inches="tight")
    cluster_scatter(model, students).savefig(OUTPUT_DIR / "clusters_pca.png", dpi=150, bbox_inches="tight")

    resources = load_resources()
    lines = ["# Evaluation report", ""]

    lines += ["## 1. Choosing k (silhouette)", "",
              md_table(["k", "Inertia", "Silhouette"],
                       [(int(r.k), f"{r.inertia:.2f}", f"{r.silhouette:.3f}") for r in model.k_scores.itertuples()]),
              "", f"Chosen k = **{model.k}** (silhouette **{model.silhouette:.3f}**).", ""]

    lines += ["## 2. Do clusters match the hidden archetypes?", "",
              f"Adjusted Rand Index vs. the synthetic ground truth: **{ari:.3f}** "
              "(1.0 = perfect match, 0 = random). This is a sanity check on synthetic data, "
              "not proof the archetypes exist in real learners.", ""]

    lines += ["## 3. Cluster profiles", "",
              md_table(["Cluster", "Name", "Focus"] + [TOPIC_LABELS[t] for t in TOPICS],
                       [(i, p.name, p.focus, *[f"{v:.2f}" for v in p.centroid]) for i, p in model.profiles.items()]),
              ""]

    lines += ["## 4. Recommender on hand-made profiles", "",
              "Check each path makes sense for the profile (6 study hours per week).", ""]
    rows, passes = [], 0
    for name, skills in DEMO_PROFILES.items():
        cid, prof = assign_cluster(model, skills)
        rec = recommend(skills, resources, hours_per_week=6)
        rows.append((name, prof.name, " → ".join(rec["id"].head(5)) + " ...",
                     ", ".join(TOPIC_LABELS[t] for t in rec["topic"].unique())))
    for name, skills, expected in EXTRA_PROFILES:
        cid, prof = assign_cluster(model, skills)
        rec = recommend(skills, resources, hours_per_week=6)
        ok = expected in set(rec["topic"])
        passes += ok
        rows.append((name, prof.name, " → ".join(rec["id"].head(5)) + " ...",
                     ", ".join(TOPIC_LABELS[t] for t in rec["topic"].unique())
                     + f"  | expected topic '{expected}': {'PASS' if ok else 'FAIL'}"))
    lines += [md_table(["Profile", "Learner type", "First 5 resource ids", "Topics covered"], rows), "",
              f"Expected-topic checks passed: **{passes}/{len(EXTRA_PROFILES)}**.", ""]

    report = "\n".join(lines)
    (OUTPUT_DIR / "evaluation_report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved plots and report to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
