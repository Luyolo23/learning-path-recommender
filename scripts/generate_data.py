"""Generate data/synthetic_students.csv (run from the project root).

    python scripts/generate_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import STUDENTS_PATH  # noqa: E402
from src.data_generation import generate_students  # noqa: E402

if __name__ == "__main__":
    df = generate_students(n=300)
    df.to_csv(STUDENTS_PATH, index=False)
    print(f"Wrote {len(df)} synthetic learners to {STUDENTS_PATH}")
    print(df["true_archetype"].value_counts().to_string())
