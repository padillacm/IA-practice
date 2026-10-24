import unittest

from title_dedup import Record, dedupe


def rec(i, title, year=2020, kind="movie", **meta):
    return Record(i, title, year, kind, meta)


class DedupeTest(unittest.TestCase):
    def test_groups_case_and_accent_variants(self):
        groups = dedupe([rec("b", "AMÉLIE", 2001, synopsis="x"), rec("a", "Amelie", 2001)])
        self.assertEqual(groups, [{"canonical": "b", "duplicates": ["a"]}])

    def test_same_title_different_year_not_merged(self):
        groups = dedupe([rec("a", "Dune", 1984), rec("b", "Dune", 2021)])
        self.assertEqual([g["duplicates"] for g in groups], [[], []])

    def test_same_title_different_kind_not_merged(self):
        groups = dedupe([rec("a", "Narcos", 2015, "series"), rec("b", "Narcos", 2015, "movie")])
        self.assertEqual(len(groups), 2)

    def test_missing_year_only_matches_missing_year(self):
        groups = dedupe([rec("a", "Dune", None), rec("b", "Dune", 2021), rec("c", "Dune", None)])
        self.assertEqual({g["canonical"]: g["duplicates"] for g in groups}, {"a": ["c"], "b": []})

    def test_tie_goes_to_lowest_id(self):
        groups = dedupe([rec("z", "The Crown", 2016, "series"), rec("m", "Crown", 2016, "series")])
        self.assertEqual(groups, [{"canonical": "m", "duplicates": ["z"]}])

    def test_empty_metadata_values_do_not_count(self):
        groups = dedupe([rec("a", "Roma", 2018, synopsis="", cast=[]), rec("b", "ROMA", 2018, synopsis="s")])
        self.assertEqual(groups[0]["canonical"], "b")

    def test_regional_qualifier_kept_apart(self):
        groups = dedupe([rec("a", "The Office (US)", 2005, "series"), rec("b", "The Office (UK)", 2005, "series")])
        self.assertEqual(len(groups), 2)

    def test_empty_input(self):
        self.assertEqual(dedupe([]), [])


if __name__ == "__main__":
    unittest.main()
