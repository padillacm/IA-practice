import unittest

from title_dedup import normalize_title


class NormalizeTest(unittest.TestCase):
    def test_case_and_punctuation(self):
        self.assertEqual(normalize_title("Stranger Things!"), "stranger things")

    def test_accents(self):
        self.assertEqual(normalize_title("Amélie"), "amelie")

    def test_ampersand(self):
        self.assertEqual(normalize_title("Fast & Furious"), normalize_title("Fast and Furious"))

    def test_leading_article(self):
        self.assertEqual(normalize_title("The Crown"), "crown")
        self.assertEqual(normalize_title("A Quiet Place"), "quiet place")

    def test_lone_article_kept(self):
        self.assertEqual(normalize_title("The"), "the")

    def test_qualifiers_keep_identity(self):
        self.assertNotEqual(normalize_title("The Office (US)"), normalize_title("The Office (UK)"))

    def test_whitespace(self):
        self.assertEqual(normalize_title("  Dark   Matter "), "dark matter")


if __name__ == "__main__":
    unittest.main()
