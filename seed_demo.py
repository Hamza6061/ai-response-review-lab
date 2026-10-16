"""Create an explicitly synthetic set of annotations in a NEW demo database."""
import argparse
from pathlib import Path
from app import DIMENSIONS, ROOT, connect, load_cases, save_review, summary, all_reviews
import json


def seed(path):
    path = Path(path)
    # Exclusive creation prevents overwriting genuine annotations.
    with path.open('xb'):
        pass
    cases = load_cases(ROOT / 'cases.json')
    first = ['response_1', 'response_2', 'response_2', 'response_1', 'tie', 'both_poor']
    second = ['response_1', 'response_2', 'response_1', 'response_1', 'tie', 'both_poor']
    with connect(path) as db:
        for alias, decisions in [('SYNTHETIC-reviewer-1', first), ('SYNTHETIC-reviewer-2', second)]:
            for case, choice in zip(cases, decisions):
                scores = {}
                for key in ('response_1', 'response_2'):
                    rating = 1 if choice == 'both_poor' else 5 if choice in (key, 'tie') else 2
                    scores[key] = {d: rating for d in DIMENSIONS}
                save_review(db, dict(reviewer=alias, case_id=case['id'], choice=choice,
                    scores=scores, confidence='medium',
                    rationale='SYNTHETIC DEMO annotation for exercising agreement calculations; not a real human judgment.'), cases)
        return summary(all_reviews(db))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(ROOT / 'demo.sqlite3'))
    args = parser.parse_args()
    try:
        print(json.dumps(seed(args.db), indent=2))
    except FileExistsError:
        parser.exit(2, 'Demo database already exists. Choose another --db path.\n')
