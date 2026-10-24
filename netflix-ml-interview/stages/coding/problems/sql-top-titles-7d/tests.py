import random
import sqlite3
import unittest
from collections import Counter, defaultdict
from datetime import date, timedelta

import solution

SCHEMA = """CREATE TABLE plays(play_id INTEGER PRIMARY KEY, user_id INTEGER, title_id INTEGER, country TEXT,
play_date TEXT, completed INTEGER);"""


def make_db(rows):
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO plays VALUES (?,?,?,?,?,?)", rows)
    return con


def run(rows, as_of, n):
    con = make_db(rows)
    try:
        return [tuple(r) for r in con.execute(solution.top_titles_query(), {"as_of": as_of, "n": n}).fetchall()]
    finally:
        con.close()


def expected(rows, as_of, n):
    end = date.fromisoformat(as_of)
    start = end - timedelta(days=6)
    per = defaultdict(Counter)
    for _, _, title, country, d, done in rows:
        if done == 1 and start <= date.fromisoformat(d) <= end:
            per[country][title] += 1
    out = []
    for country in sorted(per):
        ranked = sorted(per[country].items(), key=lambda kv: (-kv[1], kv[0]))[:n]
        out += [(country, t, c, i + 1) for i, (t, c) in enumerate(ranked)]
    return out


class TestTopTitles(unittest.TestCase):
    def test_hand_case(self):
        rows = [
            (1, 1, 10, "US", "2026-03-10", 1), (2, 2, 10, "US", "2026-03-10", 1),
            (3, 3, 11, "US", "2026-03-09", 1), (4, 4, 11, "US", "2026-03-09", 1),   # tie with title 10
            (5, 5, 12, "US", "2026-03-04", 1),   # one day before the window (as_of 03-10 -> starts 03-04): included
            (6, 6, 13, "US", "2026-03-03", 1),   # outside
            (7, 7, 10, "US", "2026-03-10", 0),   # not completed
            (8, 8, 20, "BR", "2026-03-10", 1),
            (9, 9, 21, "BR", "2026-03-11", 1),   # after as_of
        ]
        self.assertEqual(run(rows, "2026-03-10", 2),
                         [("BR", 20, 1, 1), ("US", 10, 2, 1), ("US", 11, 2, 2)])
        self.assertEqual(run(rows, "2026-03-10", 3)[-1], ("US", 12, 1, 3))

    def test_zero_completion_titles_excluded_and_empty(self):
        rows = [(1, 1, 5, "MX", "2026-03-10", 0)]
        self.assertEqual(run(rows, "2026-03-10", 3), [])
        self.assertEqual(run([], "2026-03-10", 3), [])

    def test_matches_python_oracle_on_random_data(self):
        rng = random.Random(4)
        base = date(2026, 3, 1)
        rows = [(i, rng.randint(1, 50), rng.randint(1, 12), rng.choice(["US", "BR", "FR", "JP"]),
                 (base + timedelta(days=rng.randint(0, 20))).isoformat(), rng.choice([0, 1, 1]))
                for i in range(1, 600)]
        for as_of in ("2026-03-08", "2026-03-15", "2026-03-21"):
            for n in (1, 3, 5):
                self.assertEqual(run(rows, as_of, n), expected(rows, as_of, n), (as_of, n))


if __name__ == "__main__":
    unittest.main()
