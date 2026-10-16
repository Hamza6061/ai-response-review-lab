"""AI Response Review Lab: a local, standard-library human evaluation app."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DIMENSIONS = ('accuracy', 'relevance', 'clarity', 'instructions')
CHOICES = ('response_1', 'response_2', 'tie', 'both_poor')


def load_cases(path):
    cases = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(cases, list) or not cases:
        raise ValueError('Dataset must be a non-empty array')
    ids = set()
    for case in cases:
        for key in ('id', 'category', 'prompt', 'reference', 'response_1', 'response_2'):
            if not isinstance(case.get(key), str) or not case[key].strip():
                raise ValueError('Each case needs non-empty text: ' + key)
        if case['id'] in ids:
            raise ValueError('Duplicate case id')
        ids.add(case['id'])
    return cases


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS reviews (
        reviewer TEXT NOT NULL, case_id TEXT NOT NULL, payload TEXT NOT NULL,
        updated_at TEXT NOT NULL, PRIMARY KEY(reviewer, case_id))''')
    return db


def order_for(reviewer, case_id):
    digest = hashlib.sha256((reviewer + ':' + case_id).encode()).digest()
    return ['response_1', 'response_2'] if digest[0] % 2 == 0 else ['response_2', 'response_1']


def save_review(db, payload, cases):
    if not isinstance(payload, dict):
        raise ValueError('Review must be an object')
    reviewer = payload.get('reviewer')
    if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 60:
        raise ValueError('Reviewer alias must contain 1–60 characters')
    reviewer = reviewer.strip()
    case_id = payload.get('case_id')
    if case_id not in {c['id'] for c in cases}:
        raise ValueError('Unknown case')
    scores = payload.get('scores')
    if not isinstance(scores, dict):
        raise ValueError('Both response score sets are required')
    for answer in ('response_1', 'response_2'):
        if not isinstance(scores.get(answer), dict) or set(scores[answer]) != set(DIMENSIONS):
            raise ValueError('Each response requires all four dimensions')
        if any(type(value) is not int or not 1 <= value <= 5 for value in scores[answer].values()):
            raise ValueError('Scores must be integers from 1 to 5')
    if payload.get('choice') not in CHOICES:
        raise ValueError('Choose a preferred response, tie, or both poor')
    rationale = payload.get('rationale')
    if not isinstance(rationale, str) or not 20 <= len(rationale.strip()) <= 2000:
        raise ValueError('Give a rationale of 20–2000 characters')
    confidence = payload.get('confidence')
    if confidence not in ('low', 'medium', 'high'):
        raise ValueError('Choose confidence')
    clean = dict(reviewer=reviewer, case_id=case_id, scores=scores,
                 choice=payload['choice'], rationale=rationale.strip(), confidence=confidence)
    timestamp = datetime.now(timezone.utc).isoformat()
    with db:
        db.execute('INSERT OR REPLACE INTO reviews VALUES (?, ?, ?, ?)',
                   (reviewer, case_id, json.dumps(clean), timestamp))
    return clean


def all_reviews(db):
    return [{**json.loads(r['payload']), 'updated_at': r['updated_at']}
            for r in db.execute('SELECT payload, updated_at FROM reviews ORDER BY reviewer, case_id')]


def agreement(left, right):
    """Unweighted Cohen kappa on four canonical preference categories."""
    shared = sorted(set(left) & set(right))
    if not shared:
        return {'paired_cases': 0, 'agreement': None, 'kappa': None}
    n = len(shared)
    observed = sum(left[k] == right[k] for k in shared) / n
    a = Counter(left[k] for k in shared)
    b = Counter(right[k] for k in shared)
    expected = sum(a[c] * b[c] for c in CHOICES) / (n * n)
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return {'paired_cases': n, 'agreement': observed, 'kappa': kappa}


def summary(reviews):
    people = sorted({r['reviewer'] for r in reviews})
    pairs = []
    for i, first in enumerate(people):
        for second in people[i + 1:]:
            a = {r['case_id']: r['choice'] for r in reviews if r['reviewer'] == first}
            b = {r['case_id']: r['choice'] for r in reviews if r['reviewer'] == second}
            pairs.append({'reviewers': [first, second], **agreement(a, b)})
    votes = Counter(r['choice'] for r in reviews)
    return {'reviews': len(reviews), 'reviewers': len(people),
            'cases_reviewed': len({r['case_id'] for r in reviews}),
            'preferences': {c: votes[c] for c in CHOICES}, 'agreement': pairs}


def make_server(host, port, database, cases):
    token = secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def send(self, value, status=200, mime='application/json', download=False):
            content = value.encode() if isinstance(value, str) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if download:
                self.send_header('Content-Disposition', 'attachment; filename="reviews.json"')
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/':
                return self.send((ROOT / 'index.html').read_text().replace('__TOKEN__', token), mime='text/html')
            if url.path == '/api/cases':
                reviewer = parse_qs(url.query).get('reviewer', [''])[0].strip()
                if not 1 <= len(reviewer) <= 60:
                    return self.send({'error': 'Enter a reviewer alias of 1–60 characters'}, 400)
                with connect(database) as db:
                    saved = {r['case_id']: r for r in all_reviews(db) if r['reviewer'] == reviewer}
                return self.send([{'case': c, 'order': order_for(reviewer, c['id']),
                                   'saved': saved.get(c['id'])} for c in cases])
            if url.path in ('/api/summary', '/api/export'):
                with connect(database) as db:
                    reviews = all_reviews(db)
                return self.send(summary(reviews) if url.path.endswith('summary') else reviews,
                                 download=url.path.endswith('export'))
            self.send({'error': 'Not found'}, 404)

        def do_POST(self):
            if self.path != '/api/reviews':
                return self.send({'error': 'Not found'}, 404)
            if self.headers.get('X-Review-Token') != token:
                return self.send({'error': 'Reload the application before saving'}, 403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20000:
                    raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(length))
                with connect(database) as db:
                    result = save_review(db, payload, cases)
                self.send(result)
            except (ValueError, TypeError, KeyError) as exc:
                self.send({'error': str(exc)}, 400)
    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--db', default=str(ROOT / 'reviews.sqlite3'))
    parser.add_argument('--cases', default=str(ROOT / 'cases.json'))
    args = parser.parse_args()
    cases = load_cases(args.cases)
    connect(args.db).close()
    server = make_server(args.host, args.port, args.db, cases)
    print(f'Open http://{args.host}:{server.server_port} — Ctrl+C to stop', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
