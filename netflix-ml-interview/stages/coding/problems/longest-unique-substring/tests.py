import random
import unittest

import solution


def naive(s):
    best = (0, 0)
    for i in range(len(s)):
        seen = set()
        for j in range(i, len(s)):
            if s[j] in seen:
                break
            seen.add(s[j])
            if j - i + 1 > best[1]:
                best = (i, j - i + 1)
    return best


class TestLongest(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(solution.longest_unique_substring("abcabcbb"), 3)
        self.assertEqual(solution.longest_unique_substring("bbbbb"), 1)
        self.assertEqual(solution.longest_unique_substring("pwwkew"), 3)
        self.assertEqual(solution.longest_unique_substring(""), 0)
        self.assertEqual(solution.longest_unique_substring("abba"), 2)

    def test_span_first_longest(self):
        self.assertEqual(solution.longest_unique_span("abcabcbb"), (0, 3))
        self.assertEqual(solution.longest_unique_span("pwwkew"), (2, 3))
        self.assertEqual(solution.longest_unique_span(""), (0, 0))
        self.assertEqual(solution.longest_unique_span("abba"), (0, 2))

    def test_unicode(self):
        self.assertEqual(solution.longest_unique_substring("ñandú ñ"), 6)
        self.assertEqual(solution.longest_unique_substring("日本日本語"), 3)

    def test_matches_naive(self):
        rng = random.Random(2)
        for _ in range(500):
            s = "".join(rng.choice("abcd") for _ in range(rng.randint(0, 15)))
            self.assertEqual(solution.longest_unique_span(s), naive(s), s)

    def test_linear_time(self):
        s = "".join(chr(97 + i % 26) for i in range(500_000))
        self.assertEqual(solution.longest_unique_substring(s), 26)


if __name__ == "__main__":
    unittest.main()
