import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app import (DIMENSIONS, ROOT, agreement, all_reviews, connect, load_cases,
                 make_server, order_for, save_review, summary)


def review(alias='one', case='arithmetic', choice='response_1'):
    return {'reviewer': alias, 'case_id': case, 'choice': choice,
            'scores': {k: {d: 4 for d in DIMENSIONS} for k in ('response_1', 'response_2')},
            'confidence': 'high', 'rationale': 'Synthetic test rationale with enough detail.'}


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases(ROOT / 'cases.json')
        self.db = connect(':memory:')

    def tearDown(self):
        self.db.close()

    def test_valid_review_and_revision(self):
        save_review(self.db, review(), self.cases)
        save_review(self.db, review(choice='tie'), self.cases)
        self.assertEqual(len(all_reviews(self.db)), 1)
        self.assertEqual(all_reviews(self.db)[0]['choice'], 'tie')

    def test_distinct_reviewers_preserved(self):
        for alias in ['one', 'two']:
            save_review(self.db, review(alias), self.cases)
        self.assertEqual(summary(all_reviews(self.db))['reviewers'], 2)

    def test_reject_invalid_ratings(self):
        for score in (0, 6, True, '4'):
            payload = review()
            payload['scores']['response_1']['accuracy'] = score
            with self.assertRaises(ValueError):
                save_review(self.db, payload, self.cases)

    def test_reject_missing_dimension(self):
        payload = review()
        del payload['scores']['response_1']['accuracy']
        with self.assertRaises(ValueError):
            save_review(self.db, payload, self.cases)

    def test_reject_invalid_case_choice_rationale(self):
        for key, value in [('case_id', 'missing'), ('choice', 'A'), ('rationale', 'short'), ('reviewer', '  '), ('confidence', 'certain')]:
            payload = review()
            payload[key] = value
            with self.assertRaises(ValueError):
                save_review(self.db, payload, self.cases)

    def test_order_stable_and_balanced_across_aliases(self):
        order = order_for('one', 'arithmetic')
        self.assertEqual(order, order_for('one', 'arithmetic'))
        self.assertEqual(set(order), {'response_1', 'response_2'})
        self.assertEqual(len({tuple(order_for(str(i), 'arithmetic')) for i in range(100)}), 2)

    def test_kappa_perfect_nonconstant(self):
        choices = {'a': 'response_1', 'b': 'tie'}
        self.assertEqual(agreement(choices, choices)['kappa'], 1)

    def test_kappa_known_disagreement(self):
        a = {'a': 'response_1', 'b': 'response_2'}
        b = {'a': 'response_2', 'b': 'response_1'}
        self.assertEqual(agreement(a, b)['kappa'], -1)

    def test_no_overlap_and_constant_labels(self):
        self.assertIsNone(agreement({'a': 'tie'}, {'b': 'tie'})['agreement'])
        self.assertIsNone(agreement({'a': 'tie'}, {'a': 'tie'})['kappa'])

    def test_overlap_only(self):
        result = agreement({'a': 'tie', 'b': 'response_1'}, {'a': 'tie'})
        self.assertEqual(result['paired_cases'], 1)
        self.assertEqual(result['agreement'], 1)

    def test_persistence_after_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.sqlite3'
            db = connect(path)
            save_review(db, review(), self.cases)
            db.close()
            with connect(path) as reopened:
                self.assertEqual(all_reviews(reopened)[0]['reviewer'], 'one')

    def test_duplicate_dataset_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cases.json'
            path.write_text(json.dumps([self.cases[0], self.cases[0]]))
            with self.assertRaises(ValueError):
                load_cases(path)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = make_server('127.0.0.1', 0, str(Path(cls.temp.name) / 'test.sqlite3'), load_cases(ROOT / 'cases.json'))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def test_page_and_case_endpoint(self):
        with urlopen(self.base) as response:
            page = response.read().decode()
        self.assertIn('AI Response Review Lab', page)
        self.assertNotIn('__TOKEN__', page)
        with urlopen(self.base + '/api/cases?reviewer=one') as response:
            self.assertEqual(len(json.load(response)), 6)

    def test_save_and_export_end_to_end(self):
        with urlopen(self.base) as response:
            page = response.read().decode()
        token = page.split("const TOKEN='")[1].split("'")[0]
        data = json.dumps(review()).encode()
        request = Request(self.base + '/api/reviews', data=data,
                          headers={'X-Review-Token': token, 'Content-Type': 'application/json'})
        with urlopen(request) as response:
            self.assertEqual(json.load(response)['case_id'], 'arithmetic')
        with urlopen(self.base + '/api/export') as response:
            self.assertIn('attachment', response.headers['Content-Disposition'])
            self.assertTrue(any(r['reviewer'] == 'one' for r in json.load(response)))

    def test_save_without_token_forbidden(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.base + '/api/reviews', data=b'{}'))
        self.assertEqual(error.exception.code, 403)

    def test_unknown_route(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + '/missing')
        self.assertEqual(error.exception.code, 404)

if __name__ == '__main__':
    unittest.main()
