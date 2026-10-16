# AI Response Review Lab

A working, AI-assisted Python application for **pairwise human evaluation of AI responses**. Reviewers compare blinded answers, score four dimensions, explain their preference, and examine agreement with other reviewers.

Built as a portfolio project for AI evaluation and annotation work. All bundled prompts, answers, references and demonstration ratings are synthetic. No real model outputs or human research results are claimed.

## Run in GitHub Codespaces
1. Click **Code → Codespaces → Create codespace on main** in this repository.
2. In the Terminal, run:
   ```sh
   python app.py --host 0.0.0.0
   ```
3. Open forwarded **port 8000** using the notification or the **Ports** tab. Keep the port visibility **Private**.
4. Enter a reviewer alias, such as `reviewer-01`, and click **Load reviews**.
5. Read the rubric, prompt, reference, and answers. Score every dimension, select your preference and confidence, and write a specific rationale. Click **Save review**.
6. Repeat under a different alias to simulate a second reviewer, or have a second person use the same running app. The dashboard compares overlapping cases. An alias is not an authenticated identity.
7. Click **Export saved reviews** to download JSON. Stop the Codespace when finished.

Python 3.10+ is required. **No third-party packages, API keys or paid model services are needed.** A GitHub Codespace can have usage charges depending on your account's allowance. The app itself is free to run locally.

## Run on your computer / PyCharm
Open this repository folder in PyCharm, choose a Python 3.10+ interpreter, and run `app.py`. Or use the terminal:
```sh
python app.py
```
Visit **http://127.0.0.1:8000** in your browser. Press Ctrl+C in the terminal to stop it. By default the database lives beside `app.py` in `reviews.sqlite3`. Your reviews survive browser refreshes and server restarts while that file exists.

## Explore a clearly labelled demonstration
Stop the normal app first, then run:
```sh
python seed_demo.py
python app.py --db demo.sqlite3
```
For Codespaces, add `--host 0.0.0.0` to the second command.

`seed_demo.py` refuses to overwrite an existing file. It creates twelve artificial ratings by two aliases named `SYNTHETIC-reviewer-1` and `SYNTHETIC-reviewer-2`. The preloaded decisions deliberately disagree on one of six cases. The dashboard therefore shows **83.3% preference agreement** and **Cohen's κ ≈ 0.769**. These are software fixtures, not evidence about real reviewers or a model. Use a different database for your real annotations.

## What makes this useful
- **Stable A/B ordering:** a SHA-256-based assignment changes answer positions across aliases while preserving each reviewer's assignment. It reduces a fixed-position cue; it does not ensure experimental balance on small samples.
- **Independent ratings:** accuracy, relevance, clarity, and instruction following each receive 1–5 scores.
- **Explicit decisions:** prefer A, prefer B, tie, or reject both, with confidence and a rationale.
- **Saved annotations:** SQLite retains one current review per alias/case. Saving again updates that review rather than double-counting it.
- **Agreement analysis:** pairwise overlap, raw preference agreement, and unweighted Cohen's kappa on canonical answer identities.
- **Portable output:** JSON export includes scores, decisions, rationale and update timestamps.
- **Local execution:** no external model requests, analytics or browser storage services.

## Review protocol
1. Use a frozen prompt set and agree on the rubric before annotation.
2. Review independently, using aliases that uniquely identify reviewers.
3. Read the supplied reference as task guidance, not as a substitute for thinking.
4. Score each answer independently, then choose a preference based primarily on correctness and explicit instructions.
5. Give a rationale that quotes or points to a concrete error or strength.
6. Compare agreement only after independent reviews. Use disagreements for adjudication and rubric refinement.
7. Export a copy before deleting a Codespace or moving the database.

The interface does not autosave. Save before moving between cases or switching aliases. The latest saved review is restored when you return.

## Rubric
| Dimension | Review question |
|---|---|
| Accuracy | Are the facts, calculations, reasoning and evidence use correct? |
| Relevance | Does it address the requested task? |
| Clarity | Is it understandable and well expressed? |
| Instruction following | Does it meet the explicit scope and format? |

For each dimension: **1** major failure; **2** substantial problems; **3** mixed/needs revision; **4** minor issues; **5** fully meets the criterion. A wrong answer can still be clearly written. `Tie` means comparable quality; `Both poor` means neither is acceptable.

## Agreement calculation and limits
For each pair of aliases, let N be the number of cases both reviewed. Observed agreement is the fraction with equal canonical preference labels. Expected agreement is the sum of the products of their marginal proportions across `response_1`, `response_2`, `tie` and `both_poor`.

`κ = (observed agreement − expected agreement) / (1 − expected agreement)`

The app returns N/A for no overlap and for κ when the denominator is zero. It does not calculate confidence intervals or agreement on numeric ratings. Agreement does not establish correctness, and small synthetic samples cannot support conclusions about model quality. Exports expose canonical identities for analysis; the review interface displays A/B without source labels.

## Tests
```sh
python -m unittest -v
```
The suite covers validation, revision/upsert behavior, persistence, stable assignments, known kappa values, no overlap, undefined kappa, malformed datasets, HTTP routes, request-token protection, and save/export integration.

## Project files
| File | Purpose |
|---|---|
| app.py | HTTP API, SQLite storage, validation, ordering and agreement |
| index.html | Responsive review interface and dashboard |
| cases.json | Six authored prompt pairs with reference guidance |
| seed_demo.py | Explicitly synthetic demo annotations in a separate database |
| test_app.py | Unit and HTTP integration tests |
| HANDSHAKE.md | Portfolio description and demonstration guide |
| VALIDATION.md | Results from development checks |

## Scope and trust model
This is a local educational prototype, not a public annotation platform. There is no login, reviewer isolation, audit history or role management. Anyone who can access the running app can view the export and edit an alias's reviews. The request token guards ordinary cross-site writes; it is not authentication. Use localhost or a private forwarded Codespaces port, not a publicly exposed server. No real personal or confidential data is needed.

Keep `cases.json` unchanged while collecting reviews. To change prompts, answer wording or rubric, start a new database: this prototype has no dataset-version migration. Databases are intentionally excluded from Git to avoid publishing annotations accidentally. The supplied references are manually authored for elementary examples, not external citations.

## How AI was used and what to learn
ChatGPT helped generate the code, sample tasks, tests, and documentation. Development validation was performed in the assistant's environment. Review the implementation and run it yourself before claiming personal testing or independent authorship.

The learning goal is to practise task specification, rubric-based judgment, evidence-grounded rationales, persistent annotation design, and the difference between agreement and accuracy. Future work could add authenticated reviewers, adjudication, immutable dataset versions, audit history, real licensed model responses and uncertainty intervals. Those features are not implemented.
