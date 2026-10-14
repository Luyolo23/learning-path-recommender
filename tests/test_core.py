"""Unit tests. Run from the project root with either:

    python -m unittest discover -s tests -v
    pytest

No network access or API key is needed (the LLM is replaced by a fake).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.clustering import assign_cluster, describe_cluster, train_cluster_model  # noqa: E402
from src.config import DEMO_PROFILES, TOPIC_ORDER, TOPICS  # noqa: E402
from src.data_generation import generate_students  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402
from src.planner import merge_llm_text, plan_to_markdown, schedule_resources  # noqa: E402
from src.quiz import load_questions, score_answers  # noqa: E402
from src.recommender import load_resources, recommend  # noqa: E402

STUDENTS = generate_students()
MODEL = train_cluster_model(STUDENTS)
RESOURCES = load_resources()
QUESTIONS = load_questions()


class QuizTests(unittest.TestCase):
    def test_all_correct_gives_full_scores(self):
        answers = {q["id"]: q["answer"] for q in QUESTIONS}
        scores = score_answers(answers, QUESTIONS)
        self.assertEqual(set(scores), set(TOPICS))
        self.assertTrue(all(v == 1.0 for v in scores.values()))

    def test_unanswered_gives_zero(self):
        scores = score_answers({}, QUESTIONS)
        self.assertTrue(all(v == 0.0 for v in scores.values()))

    def test_every_topic_has_questions(self):
        self.assertEqual({q["topic"] for q in QUESTIONS}, set(TOPICS))


class DataTests(unittest.TestCase):
    def test_shape_and_range(self):
        self.assertEqual(len(STUDENTS), 300)
        self.assertTrue(STUDENTS[TOPICS].min().min() >= 0.0)
        self.assertTrue(STUDENTS[TOPICS].max().max() <= 1.0)

    def test_reproducible(self):
        a, b = generate_students(seed=1), generate_students(seed=1)
        self.assertTrue(a.equals(b))

    def test_catalogue_covers_every_topic_and_level(self):
        for t in TOPICS:
            self.assertGreaterEqual((RESOURCES["topic"] == t).sum(), 3, t)
        self.assertEqual(set(RESOURCES["difficulty"]), {1, 2, 3})


class ClusteringTests(unittest.TestCase):
    def test_quality(self):
        self.assertGreater(MODEL.silhouette, 0.3)
        self.assertIn(MODEL.k, range(3, 8))

    def test_assignment_matches_obvious_profiles(self):
        _, beginner = assign_cluster(MODEL, DEMO_PROFILES["Beginner across the board"])
        self.assertEqual(beginner.focus, "beginner")
        _, well = assign_cluster(MODEL, DEMO_PROFILES["Well-rounded intermediate"])
        self.assertEqual(well.focus, "balanced")

    def test_describe_cluster_beginner(self):
        self.assertEqual(describe_cluster([0.1] * 6).focus, "beginner")

    def test_profile_names_unique(self):
        names = [p.name for p in MODEL.profiles.values()]
        self.assertEqual(len(names), len(set(names)))


class RecommenderTests(unittest.TestCase):
    def test_weak_python_gets_python_first(self):
        rec = recommend(DEMO_PROFILES["Beginner across the board"], RESOURCES, hours_per_week=6)
        self.assertEqual(rec.iloc[0]["topic"], "python")

    def test_strong_python_weak_ml_gets_ml(self):
        skills = dict(python=1.0, data=1.0, prompting=1.0, ml=0.0, evaluation=0.33, ethics=1.0)
        rec = recommend(skills, RESOURCES, hours_per_week=6)
        self.assertIn("ml", set(rec["topic"]))
        self.assertNotIn("python", set(rec["topic"]))

    def test_order_respects_prerequisites(self):
        for skills in DEMO_PROFILES.values():
            rec = recommend(skills, RESOURCES, hours_per_week=6)
            idx = [TOPIC_ORDER.index(t) for t in rec["topic"]]
            self.assertEqual(idx, sorted(idx))

    def test_max_per_topic_and_length(self):
        rec = recommend(DEMO_PROFILES["Beginner across the board"], RESOURCES, n=8, max_per_topic=2)
        self.assertLessEqual(len(rec), 8)
        self.assertLessEqual(rec["topic"].value_counts().max(), 2)

    def test_strong_everywhere_gets_stretch_resources(self):
        rec = recommend({t: 1.0 for t in TOPICS}, RESOURCES)
        self.assertFalse(rec.empty)
        self.assertTrue(rec["reason"].str.startswith("Stretch").all())

    def test_goal_text_changes_the_path(self):
        skills = DEMO_PROFILES["Well-rounded intermediate"]
        plain = set(recommend(skills, RESOURCES, hours_per_week=6)["id"])
        goal = set(recommend(skills, RESOURCES, hours_per_week=6,
                             goal_text="prompt engineering for chatbots and LLM")["id"])
        self.assertNotEqual(plain, goal)

    def test_very_long_resources_avoided_on_small_budget(self):
        rec = recommend(DEMO_PROFILES["Beginner across the board"], RESOURCES, hours_per_week=3)
        self.assertTrue((rec["hours"] <= 12).all())

    def test_missing_topic_raises(self):
        with self.assertRaises(ValueError):
            recommend({"python": 0.5}, RESOURCES)


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.skills = DEMO_PROFILES["Practical coder, light on theory"]
        self.rec = recommend(self.skills, RESOURCES, hours_per_week=6)
        self.profile = assign_cluster(MODEL, self.skills)[1]

    def test_schedule_places_every_resource_once(self):
        schedule, stretch = schedule_resources(self.rec, 6)
        placed = [i for ids in schedule.values() for i in ids] + stretch
        self.assertEqual(sorted(placed), sorted(self.rec["id"]))

    def test_schedule_respects_budget_when_possible(self):
        schedule, _ = schedule_resources(self.rec, 6)
        hours = dict(zip(self.rec["id"], self.rec["hours"]))
        for ids in schedule.values():
            if len(ids) > 1:
                self.assertLessEqual(sum(hours[i] for i in ids), 6 + 1e-9)

    def _plan(self, fake_reply=None, use_llm=False, key="k"):
        caller = (lambda *a: fake_reply) if fake_reply is not None else None
        return run_pipeline(self.skills, RESOURCES, MODEL, 6, "", use_llm, key, caller=caller)

    def test_rule_based_plan_works_offline(self):
        r = self._plan()
        self.assertEqual(r.plan["source"], "rule-based")
        self.assertTrue(r.plan["weeks"])
        self.assertIn("# My 4-week learning plan", plan_to_markdown(r.plan, r.profile.name))

    def test_llm_reply_with_links_and_invented_ids_is_rejected(self):
        base = self._plan()
        first_id = base.plan["weeks"][0]["items"][0]["id"]
        reply = json.dumps({
            "summary": "Visit https://evil.example now",
            "weeks": [{"week": 1, "goal": "Learn ML basics.", "tip": "See www.spam.com",
                       "why": {first_id: "Great foundation for you.", "R99": "I made this up"}}],
        })
        r = self._plan(reply, use_llm=True)
        wk1 = r.plan["weeks"][0]
        self.assertEqual(wk1["goal"], "Learn ML basics.")           # safe text accepted
        self.assertEqual(wk1["items"][0]["why"], "Great foundation for you.")
        self.assertNotIn("evil", r.plan["summary"])                  # link rejected
        self.assertNotIn("spam", wk1["tip"])                          # link rejected
        ids = {it["id"] for wk in r.plan["weeks"] for it in wk["items"]}
        self.assertNotIn("R99", ids)                                  # no invented resource
        self.assertIsNotNone(r.notice)

    def test_invalid_json_falls_back(self):
        r = self._plan("this is not json", use_llm=True)
        self.assertEqual(r.plan["source"], "rule-based")
        self.assertIn("unavailable", r.notice)

    def test_missing_key_falls_back(self):
        r = self._plan(use_llm=True, key=None)
        self.assertEqual(r.plan["source"], "rule-based")
        self.assertIn("no Groq API key", r.notice)

    def test_merge_rejects_non_dict(self):
        with self.assertRaises(ValueError):
            merge_llm_text({"weeks": [], "summary": ""}, "[1, 2, 3]")


if __name__ == "__main__":
    unittest.main()
