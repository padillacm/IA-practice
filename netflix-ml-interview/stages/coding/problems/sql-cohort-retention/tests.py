import random
import sqlite3
import unittest
from collections import defaultdict
from datetime import date, timedelta

import solution

SCHEMA = """CREATE TABLE signups(user_id INTEGER PRIMARY KEY, signup_date TEXT);
CREATE TABLE activity(user_id INTEGER, activity_date TEXT);"""


def run(signups, activity):
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO signups VALUES (?,?)", signups)
    con.executemany("INSERT INTO activity VALUES (?,?)", activity)
    try:
        return [tuple(r) for r in con.execute(solution.cohort_retention_query()).fetchall()]
    finally:
        con.close()


def expected(signups, activity):
    sd = {u: d for u, d in signups}
    size = defaultdict(int)
    for u, d in signups:
        size[d[:7]] += 1
    act = defaultdict(set)
    for u, d in activity:
        if u in sd and d >= sd[u]:
            y0, m0 = int(sd[u][:4]), int(sd[u][5:7])
            y, m = int(d[:4]), int(d[5:7])
            act[(sd[u][:7], (y - y0) * 12 + m - m0)].add(u)
    return [(c, off, len(us), size[c], round(len(us) / size[c], 4)) for (c, off), us in sorted(act.items())]


class TestCohorts(unittest.TestCase):
    def test_hand_case(self):
        signups = [(1, "2026-01-31"), (2, "2026-01-05"), (3, "2026-01-20"), (4, "2026-02-01")]
        activity = [
            (1, "2026-01-31"), (1, "2026-02-01"), (1, "2026-02-02"),   # duplicates inside a month count once
            (2, "2026-01-04"),                                          # before signup: ignored
            (2, "2026-03-01"),                                          # offset 2, nothing in offset 1
            (4, "2026-02-10"), (4, "2026-03-10"),
            (99, "2026-02-10"),                                         # unknown user: ignored
        ]
        self.assertEqual(run(signups, activity), [
            ("2026-01", 0, 1, 3, 0.3333),
            ("2026-01", 1, 1, 3, 0.3333),
            ("2026-01", 2, 1, 3, 0.3333),
            ("2026-02", 0, 1, 1, 1.0),
            ("2026-02", 1, 1, 1, 1.0),
        ])

    def test_year_boundary(self):
        self.assertEqual(run([(1, "2025-12-15")], [(1, "2026-02-01")]), [("2025-12", 2, 1, 1, 1.0)])

    def test_no_activity(self):
        self.assertEqual(run([(1, "2026-01-01")], []), [])

    def test_matches_python_oracle(self):
        rng = random.Random(8)
        base = date(2025, 10, 1)
        signups = [(u, (base + timedelta(days=rng.randint(0, 120))).isoformat()) for u in range(1, 80)]
        activity = [(rng.randint(1, 85), (base + timedelta(days=rng.randint(0, 260))).isoformat()) for _ in range(900)]
        self.assertEqual(run(signups, activity), expected(signups, activity))


if __name__ == "__main__":
    unittest.main()
