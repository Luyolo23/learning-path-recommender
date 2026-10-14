"""One function that runs the whole flow: skills -> archetype -> path -> plan."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .clustering import ClusterModel, ClusterProfile, assign_cluster
from .planner import generate_plan
from .recommender import recommend


@dataclass
class Result:
    skills: dict
    overall: float
    cluster_id: int
    profile: ClusterProfile
    recommendations: pd.DataFrame
    plan: dict
    notice: str | None
    hours_per_week: float
    goal: str


def run_pipeline(skills: dict[str, float], resources: pd.DataFrame, cluster_model: ClusterModel,
                 hours_per_week: float = 6, goal: str = "", use_llm: bool = False,
                 api_key: str | None = None, llm_model: str | None = None, caller=None) -> Result:
    cluster_id, profile = assign_cluster(cluster_model, skills)
    rec = recommend(skills, resources, goal_text=goal, hours_per_week=hours_per_week)
    plan, notice = generate_plan(rec, profile, skills, hours_per_week, goal=goal, use_llm=use_llm,
                                 api_key=api_key, model=llm_model, caller=caller)
    return Result(skills=skills, overall=sum(skills.values()) / len(skills), cluster_id=cluster_id,
                  profile=profile, recommendations=rec, plan=plan, notice=notice,
                  hours_per_week=hours_per_week, goal=goal)
