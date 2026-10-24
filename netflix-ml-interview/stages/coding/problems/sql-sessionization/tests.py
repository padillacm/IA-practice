import random
import sqlite3
import unittest
from collections import defaultdict

import solution


def run(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE events(user_id INTEGER, ts INTEGER, event TEXT)")
    con.executemany("INSERT INTO events VALUES (?,?,?)", rows)
    try:
        return [tuple(r) for r in con.execute(solution.sessionize_query()).fetchall()]
    finally:
        con.close()


def expected(rows):
    per = defaultdict(list)
    for u, ts, _ in rows:
        per[u].append(ts)
    out = []
    for u in sorted(per):
        sessions = []
        for ts in sorted(per[u]):
            if sessions and ts - sessions[-1][-1] <= 1800:
                sessions[-1].append(ts)
            else:
                sessions.append([ts])
        out += [(u, i + 1, s[0], s[-1], len(s)) for i, s in enumerate(sessions)]
    return out


class TestSessions(unittest.TestCase):
    def test_boundary(self):
        rows = [(1, 0, "play"), (1, 1800, "pause"), (1, 3601, "play"), (1, 3601, "stop")]
        self.assertEqual(run(rows), [(1, 1, 0, 1800, 2), (1, 2, 3601, 3601, 2)])

    def test_multiple_users_and_unsorted_insert_order(self):
        rows = [(2, 5000, "a"), (1, 10, "a"), (2, 100, "a"), (1, 1500, "a"), (1, 4000, "a")]
        self.assertEqual(run(rows), [(1, 1, 10, 1500, 2), (1, 2, 4000, 4000, 1),
                                     (2, 1, 100, 100, 1), (2, 2, 5000, 5000, 1)])

    def test_single_event_and_empty(self):
        self.assertEqual(run([(7, 42, "x")]), [(7, 1, 42, 42, 1)])
        self.assertEqual(run([]), [])

    def test_matches_python_oracle(self):
        rng = random.Random(6)
        rows = [(rng.randint(1, 6), rng.randint(0, 40_000), "e") for _ in range(400)]
        self.assertEqual(run(rows), expected(rows))


if __name__ == "__main__":
    unittest.main()
