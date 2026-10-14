# Portfolio page template: Personalised Learning Path Recommender

Copy this into your portfolio site and replace the [brackets].

## One-line summary
An AI tool that diagnoses a learner's skill gaps and builds a prerequisite-ordered, time-aware study plan.

## The problem
Self-taught learners face hundreds of courses and no way to know what to study first. Generic roadmaps ignore what the learner already knows.

## My solution
[Screenshot or GIF of the app]
1. A short diagnostic quiz produces a skill profile across 6 topics.
2. K-Means clustering places the learner in an archetype and gives pacing advice.
3. A content-based recommender ranks resources by gap, level, prerequisites and time budget.
4. A 4-week plan is generated; an LLM (optional) only writes the wording, and its output is validated.

## Architecture
[Paste the diagram from docs/architecture.md]

## Results
- Chosen k = [5], silhouette = [0.51] (see outputs/k_selection.png)
- Adjusted Rand Index on synthetic ground truth = [0.99]
- Recommender checks on hand-made profiles: [3/3] passed (outputs/evaluation_report.md)
- User testing: [N] classmates rated plan relevance [x.x]/5. One change I made because of feedback: [...]

## Responsible AI
Privacy, transparency, synthetic-data limits, catalogue bias, labelling risk, hallucination control, human oversight. [Summarise from README]

## Tech stack
Python, pandas, scikit-learn, matplotlib, Streamlit, Groq API (optional).

## Links
[Live demo] · [GitHub repository]

## Reflection
What worked: [...]. What I would improve: [real learner data, collaborative filtering, richer quiz]. What I learned: [...].
