"""Personalised Learning Path Recommender - Streamlit app.

Run with:   streamlit run app.py

Flow: diagnostic quiz -> skill profile -> learner archetype (K-Means) ->
ranked, prerequisite-ordered resources (content-based recommender) ->
4-week plan (rule-based, optionally worded by an LLM via Groq).

SECURITY NOTE: a server-side API key (from .env or Streamlit secrets) is used
internally and is NEVER sent to the browser or shown in any widget.
"""
from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.clustering import train_cluster_model
from src.config import DEMO_PROFILES, TOPIC_LABELS, TOPICS
from src.data_generation import load_or_generate_students
from src.pipeline import run_pipeline
from src.planner import plan_to_markdown
from src.quiz import load_questions, score_answers
from src.recommender import load_resources
from src.ui import (APP_CSS, LEVELS, TOPIC_ICONS, hero_html, kpi_html, resource_card_html,
                    skill_bars_html, stepper_html)
from src.visuals import cluster_scatter, radar_chart

load_dotenv()  # reads GROQ_API_KEY / GROQ_MODEL from a local .env file if present

MAX_AI_PLANS_PER_SESSION = 3  # protects the app owner's free-tier quota on a public demo

st.set_page_config(page_title="Learning Path Recommender", page_icon="🧭", layout="wide")
st.markdown(APP_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Cached loaders (run once, not on every click)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def get_cluster_assets():
    students = load_or_generate_students()
    return students, train_cluster_model(students)


@st.cache_data(show_spinner=False)
def get_resources():
    return load_resources()


@st.cache_data(show_spinner=False)
def get_questions():
    return load_questions()


# --------------------------------------------------------------------------- #
# API key handling (server-side only)
# --------------------------------------------------------------------------- #
def server_api_key() -> str:
    """The app owner's key. Used internally, never displayed or prefilled anywhere."""
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("GROQ_API_KEY", "")  # Streamlit Cloud secrets
        except Exception:
            key = ""
    return key


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
def render_sidebar() -> dict:
    has_server_key = bool(server_api_key())
    with st.sidebar:
        st.header("⚙️ Your settings")
        hours = st.slider("Study hours per week", min_value=2, max_value=20, value=6)
        goal = st.text_input("Your goal (optional)", placeholder="e.g. build a chatbot with Python")

        st.divider()
        st.subheader("✨ AI-written plan wording")
        use_llm = st.toggle("Let an AI (Groq) write my plan", value=False)
        user_key = ""
        if use_llm:
            if has_server_key:
                left = MAX_AI_PLANS_PER_SESSION - st.session_state.get("ai_calls", 0)
                st.caption(f"AI wording is available ({max(left, 0)} left this session).")
            else:
                # Empty by default: visitors can supply their OWN key. It is never prefilled.
                user_key = st.text_input("Your Groq API key", value="", type="password",
                                         help="Free keys at console.groq.com. Used only for this session.")
            st.caption("Only your topic scores and goal text are sent. No names or personal details.")
        else:
            st.caption("Off by default. The built-in plan works fully offline.")

        st.divider()
        st.caption("🔒 Nothing you enter is stored. Quiz answers live only in this browser session.")

    api_key = user_key or (server_api_key() if use_llm else "")
    return {"hours": hours, "goal": goal, "use_llm": use_llm, "api_key": api_key,
            "model": os.getenv("GROQ_MODEL", "")}


# --------------------------------------------------------------------------- #
# Quiz
# --------------------------------------------------------------------------- #
def render_quiz(questions):
    """Show the quiz. Returns a skills dict when finished (or a demo is chosen), else None."""
    st.markdown(stepper_html(1), unsafe_allow_html=True)

    with st.expander("⚡ Just exploring? Try a demo profile instead of the quiz"):
        demo = st.selectbox("Demo profile", list(DEMO_PROFILES))
        if st.button("Use this demo profile"):
            return dict(DEMO_PROFILES[demo])

    st.subheader("Take the diagnostic quiz")
    st.caption("Six short sections, three questions each. Unsure? Take your best guess; "
               "it only adjusts your recommendations.")

    total = len(questions)
    answered = sum(st.session_state.get(f"q_{q['id']}") is not None for q in questions)
    st.progress(answered / total, text=f"{answered} of {total} questions answered")

    tabs = st.tabs([f"{TOPIC_ICONS[t]} {TOPIC_LABELS[t]}" for t in TOPICS])
    answers = {}
    for tab, topic in zip(tabs, TOPICS):
        with tab:
            section = [q for q in questions if q["topic"] == topic]
            for q in section:
                choice = st.radio(q["question"], q["options"], index=None, key=f"q_{q['id']}")
                answers[q["id"]] = None if choice is None else q["options"].index(choice)
            done = sum(answers[q["id"]] is not None for q in section)
            st.caption(f"{done}/{len(section)} answered in this section")

    complete = all(v is not None for v in answers.values())
    if not complete:
        st.info("Answer every question across all six tabs to unlock your results.")
    if st.button("Get my learning path →", type="primary", disabled=not complete):
        return score_answers(answers, questions)
    return None


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
def compute_result(skills, settings, resources, cluster_model):
    use_llm = settings["use_llm"]
    cap_notice = None
    if use_llm and st.session_state.get("ai_calls", 0) >= MAX_AI_PLANS_PER_SESSION:
        use_llm = False
        cap_notice = "You have used all AI-written plans for this session, so the built-in plan is shown."
    with st.spinner("Building your learning path..."):
        result = run_pipeline(
            skills, resources, cluster_model,
            hours_per_week=settings["hours"], goal=settings["goal"],
            use_llm=use_llm, api_key=settings["api_key"] or None,
            llm_model=settings["model"] or None,
        )
    if use_llm and settings["api_key"]:
        st.session_state["ai_calls"] = st.session_state.get("ai_calls", 0) + 1
    if cap_notice:
        result.notice = cap_notice
    return result


def render_profile(result):
    skills = result.skills
    weakest = min(skills, key=skills.get)
    strongest = max(skills, key=skills.get)
    path_hours = float(result.recommendations["hours"].sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(kpi_html("Overall score", f"{result.overall:.0%}", "across 6 topics"), unsafe_allow_html=True)
    k2.markdown(kpi_html("Strongest", TOPIC_LABELS[strongest], f"{skills[strongest]:.0%}"), unsafe_allow_html=True)
    k3.markdown(kpi_html("Biggest gap", TOPIC_LABELS[weakest], f"{skills[weakest]:.0%}"), unsafe_allow_html=True)
    k4.markdown(kpi_html("Your path", f"{len(result.recommendations)} resources",
                         f"about {path_hours:g} hours in total"), unsafe_allow_html=True)
    st.write("")

    left, right = st.columns([1, 1.1])
    with left:
        st.pyplot(radar_chart(skills))
    with right:
        st.markdown("#### Skill breakdown")
        st.markdown(skill_bars_html(skills), unsafe_allow_html=True)
        st.markdown(
            f'<div class="typebox"><div class="name">🧭 Your learner type: {result.profile.name}</div>'
            f'{result.profile.advice}</div>', unsafe_allow_html=True)


def render_path(result):
    st.caption("Ordered so prerequisites come first. Every card explains why it was chosen.")
    for _, row in result.recommendations.iterrows():
        st.markdown(resource_card_html(row.to_dict()), unsafe_allow_html=True)
    with st.expander("View as a table"):
        rec = result.recommendations
        table = rec[["order", "title", "provider", "topic", "difficulty", "format", "hours", "url"]].copy()
        table["topic"] = table["topic"].map(TOPIC_LABELS)
        table["difficulty"] = table["difficulty"].map(LEVELS)
        st.dataframe(
            table, hide_index=True,
            column_config={"order": "Step", "title": "Resource", "provider": "Provider", "topic": "Topic",
                           "difficulty": "Level", "format": "Format", "hours": "Hours",
                           "url": st.column_config.LinkColumn("Link", display_text="Open")},
        )


def render_plan(result):
    if result.notice:
        st.warning(result.notice)
    elif result.plan["source"] == "ai-worded":
        st.caption("✨ Wording written by an AI and checked automatically. The resources always come "
                   "from the recommender.")
    st.write(result.plan["summary"])

    weeks = result.plan["weeks"]
    for i in range(0, len(weeks), 2):
        cols = st.columns(2)
        for col, wk in zip(cols, weeks[i:i + 2]):
            total = sum(it["hours"] for it in wk["items"])
            with col:
                with st.container(border=True):
                    st.markdown(f"##### 🗓️ Week {wk['week']} · about {total:g} h")
                    st.markdown(f"**{wk['goal']}**")
                    for it in wk["items"]:
                        st.markdown(f"- [{it['title']}]({it['url']}) · {it['provider']} · {it['hours']:g} h  \n"
                                    f"  _{it['why']}_")
                    st.caption(f"💡 {wk['tip']}")
    if result.plan["stretch"]:
        with st.expander("If you have extra time"):
            for it in result.plan["stretch"]:
                st.markdown(f"- [{it['title']}]({it['url']}) · {it['provider']} · {it['hours']:g} h")

    st.download_button("⬇️ Download my plan (Markdown)",
                       data=plan_to_markdown(result.plan, result.profile.name),
                       file_name="my_learning_plan.md", mime="text/markdown")


def render_about():
    st.markdown(
        """
**Pipeline:** quiz → skill vector → K-Means learner type → content-based recommender
(cosine similarity between your gaps and each resource, difficulty fit, prerequisite ordering,
time budget) → 4-week schedule → optional AI wording.

**Responsible AI notes**
- **Transparent:** every recommendation shows why it was chosen.
- **The recommender is not an LLM:** it ranks resources with plain maths you can inspect.
  The optional LLM only writes friendly wording, and its output is validated (no invented resources or links).
- **Synthetic data:** learner archetypes come from generated data, not real students.
- **Limited catalogue:** it can only recommend what is in `data/resources.csv`, which reflects its author's choices.
- **Labels describe a pattern, not your ability.** A short quiz is a rough snapshot.
- **Privacy:** no names or personal data are collected or stored.
- **Human oversight:** treat this as a starting point; a teacher or mentor should have the final say.
        """
    )


def render_results(result, students, cluster_model):
    st.markdown(stepper_html(2), unsafe_allow_html=True)
    tab_profile, tab_path, tab_plan, tab_map, tab_about = st.tabs(
        ["👤 Your profile", "📚 Learning path", "🗓️ 4-week plan", "📍 Where you sit", "ℹ️ How it works"])
    with tab_profile:
        render_profile(result)
    with tab_path:
        render_path(result)
    with tab_plan:
        render_plan(result)
    with tab_map:
        st.pyplot(cluster_scatter(cluster_model, students, result.skills))
        st.caption("The learners shown are synthetic (generated), used only to find archetypes. "
                   "The star is you.")
    with tab_about:
        render_about()


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    settings = render_sidebar()
    students, cluster_model = get_cluster_assets()
    resources = get_resources()
    questions = get_questions()

    st.markdown(hero_html("🧭 Personalised Learning Path Recommender",
                          "Find out where you are, what to learn next, and in what order."),
                unsafe_allow_html=True)

    if "skills" not in st.session_state:
        skills = render_quiz(questions)
        if skills is not None:
            st.session_state["skills"] = skills
            st.session_state["result"] = compute_result(skills, settings, resources, cluster_model)
            st.rerun()
    else:
        c1, c2, _ = st.columns([1.2, 1, 3])
        if c1.button("🔄 Update plan with my settings"):
            st.session_state["result"] = compute_result(st.session_state["skills"], settings,
                                                        resources, cluster_model)
        if c2.button("↩️ Retake the quiz"):
            for key in [k for k in list(st.session_state.keys()) if k.startswith("q_")]:
                st.session_state.pop(key, None)
            for key in ["skills", "result"]:
                st.session_state.pop(key, None)
            st.rerun()
        render_results(st.session_state["result"], students, cluster_model)


main()
