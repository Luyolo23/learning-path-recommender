# Evaluation report

## 1. Choosing k (silhouette)

| k | Inertia | Silhouette |
|---|---|---|
| 3 | 39.50 | 0.422 |
| 4 | 27.22 | 0.454 |
| 5 | 17.45 | 0.514 |
| 6 | 16.66 | 0.394 |
| 7 | 16.14 | 0.324 |

Chosen k = **5** (silhouette **0.514**).

## 2. Do clusters match the hidden archetypes?

Adjusted Rand Index vs. the synthetic ground truth: **0.992** (1.0 = perfect match, 0 = random). This is a sanity check on synthetic data, not proof the archetypes exist in real learners.

## 3. Cluster profiles

| Cluster | Name | Focus | Python Programming | Data Handling & Visualisation | Prompt Engineering | Machine Learning Fundamentals | Model Evaluation | Responsible AI |
|---|---|---|---|---|---|---|---|---|
| 0 | Strong in Python Programming, growing in Model Evaluation | practice_led | 0.77 | 0.75 | 0.61 | 0.32 | 0.23 | 0.30 |
| 1 | Strong in Machine Learning Fundamentals, growing in Data Handling & Visualisation | theory_led | 0.33 | 0.28 | 0.51 | 0.76 | 0.70 | 0.69 |
| 2 | Foundations builder | beginner | 0.20 | 0.20 | 0.24 | 0.16 | 0.10 | 0.24 |
| 3 | Strong in Prompt Engineering, growing in Model Evaluation | mixed | 0.30 | 0.36 | 0.83 | 0.30 | 0.27 | 0.54 |
| 4 | Well-rounded intermediate | balanced | 0.69 | 0.69 | 0.68 | 0.63 | 0.64 | 0.60 |

## 4. Recommender on hand-made profiles

Check each path makes sense for the profile (6 study hours per week).

| Profile | Learner type | First 5 resource ids | Topics covered |
|---|---|---|---|
| Beginner across the board | Foundations builder | R01 → R02 → R08 → R09 → R10 ... | Python Programming, Data Handling & Visualisation, Machine Learning Fundamentals |
| Practical coder, light on theory | Strong in Python Programming, growing in Model Evaluation | R21 → R22 → R23 → R30 → R31 ... | Machine Learning Fundamentals, Model Evaluation, Responsible AI |
| Theory-strong, new to code | Strong in Machine Learning Fundamentals, growing in Data Handling & Visualisation | R01 → R02 → R05 → R08 → R09 ... | Python Programming, Data Handling & Visualisation, Prompt Engineering |
| Prompt-savvy, code-light | Strong in Prompt Engineering, growing in Model Evaluation | R01 → R02 → R08 → R09 → R10 ... | Python Programming, Data Handling & Visualisation, Machine Learning Fundamentals, Model Evaluation |
| Well-rounded intermediate | Well-rounded intermediate | R05 → R06 → R11 → R12 → R13 ... | Python Programming, Data Handling & Visualisation, Prompt Engineering, Machine Learning Fundamentals, Model Evaluation |
| Strong Python, no ML | Strong in Python Programming, growing in Model Evaluation | R11 → R12 → R21 → R22 → R23 ... | Data Handling & Visualisation, Machine Learning Fundamentals, Model Evaluation  | expected topic 'ml': PASS |
| No coding, strong prompting | Strong in Prompt Engineering, growing in Model Evaluation | R01 → R02 → R05 → R08 → R09 ... | Python Programming, Data Handling & Visualisation, Machine Learning Fundamentals, Model Evaluation  | expected topic 'python': PASS |
| Strong everywhere except ethics | Well-rounded intermediate | R37 → R38 → R39 ... | Responsible AI  | expected topic 'ethics': PASS |

Expected-topic checks passed: **3/3**.
