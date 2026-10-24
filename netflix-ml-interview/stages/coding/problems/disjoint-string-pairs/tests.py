import random
import unittest

import solution


def brute_count(ws):
    return sum(1 for i in range(len(ws)) for j in range(i + 1, len(ws)) if not set(ws[i]) & set(ws[j]))


def brute_prod(ws):
    return max([len(ws[i]) * len(ws[j]) for i in range(len(ws)) for j in range(i + 1, len(ws))
                if not set(ws[i]) & set(ws[j])] or [0])


class TestPairs(unittest.TestCase):
    def test_examples(self):
        ws = ["abcw", "baz", "foo", "bar", "xtfn", "abcdef"]
        self.assertEqual(solution.max_disjoint_product(ws), 16)  # abcw * xtfn
        self.assertEqual(solution.count_disjoint_pairs(["ab", "cd", "bc"]), 1)

    def test_empty_strings(self):
        self.assertEqual(solution.count_disjoint_pairs(["", "", "a"]), 3)
        self.assertEqual(solution.max_disjoint_product(["", "abc"]), 0)

    def test_duplicates(self):
        self.assertEqual(solution.count_disjoint_pairs(["ab", "ab", "cd"]), 2)
        self.assertEqual(solution.count_disjoint_pairs(["ab", "ba"]), 0)
        self.assertEqual(solution.max_disjoint_product(["ab", "abab", "cd"]), 8)

    def test_none(self):
        self.assertEqual(solution.count_disjoint_pairs([]), 0)
        self.assertEqual(solution.count_disjoint_pairs(["a"]), 0)
        self.assertEqual(solution.max_disjoint_product(["a", "a"]), 0)

    def test_matches_bruteforce(self):
        rng = random.Random(9)
        for _ in range(300):
            ws = ["".join(rng.choice("abcdefg") for _ in range(rng.randint(0, 4))) for _ in range(rng.randint(0, 12))]
            self.assertEqual(solution.count_disjoint_pairs(ws), brute_count(ws), ws)
            self.assertEqual(solution.max_disjoint_product(ws), brute_prod(ws), ws)

    def test_many_words_with_few_masks(self):
        ws = ["ab", "cd", "abab", "cdcd"] * 25_000
        self.assertEqual(solution.count_disjoint_pairs(ws), 50_000 * 50_000)


if __name__ == "__main__":
    unittest.main()
