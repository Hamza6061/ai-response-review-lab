# Handshake project entry

**Title:** AI Response Review Lab — Human Evaluation and Reviewer Agreement

**URL:** https://github.com/Hamza6061/ai-response-review-lab

## Suggested description
AI Response Review Lab is an AI-assisted Python application for comparing pairs of AI answers through structured human evaluation. Reviewers score accuracy, relevance, clarity, and instruction following, then record their preference, confidence and evidence-based rationale. Reviews are saved in SQLite and can be exported as JSON. A dashboard measures overlapping reviewer decisions using raw agreement and Cohen's kappa, correcting for A/B position changes.

I used ChatGPT to help develop the implementation, synthetic dataset, tests and documentation. The project demonstrates annotation workflow design, reproducible review, and the distinction between reviewer agreement and factual correctness. All bundled examples and demonstration annotations are synthetic; the project does not claim a live-model benchmark.

Before submitting, add your actual contributions: which cases you reviewed, a change you made, a test you ran, or a disagreement you investigated. Do not claim these activities until you perform them.

## Preview
Run the app and capture a screenshot showing a comparison with the review controls. A second screenshot can show the synthetic agreement dashboard. The demonstration remains clearly labelled synthetic.

## One-minute walkthrough
1. Start the demo database following README.md.
2. Load `SYNTHETIC-reviewer-1` and show the arithmetic pair.
3. Explain why accuracy and clarity are scored independently.
4. Show the reference guidance and a saved rationale.
5. Show the agreement dashboard: 5 of 6 paired decisions agree, but agreement alone does not prove either reviewer is correct.
6. Export the annotations and explain that real work needs independently collected human judgments.

## Ideas for your own contribution
- Write two new prompt pairs and start a fresh database.
- Review all six cases yourself, recording specific rationales.
- Ask a second person to independently review the same cases on the same private app.
- Analyse one disagreement and improve the rubric before a new review round.
