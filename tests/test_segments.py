import unittest

import pandas as pd

from tundralis.segments import normalize_segment_definitions, preview_segments


class TestSegments(unittest.TestCase):
    def test_normalizes_and_previews_nested_segment_tree(self):
        df = pd.DataFrame(
            {
                "segment": ["SMB", "Enterprise", "Enterprise", "Mid-Market"],
                "region": ["APAC", "North America", "APAC", "EMEA"],
                "overall_sat": [5, 7, 6, 3],
            }
        )
        segments = [
            {
                "name": "Enterprise APAC or high sat",
                "tree": {
                    "all": [
                        {"column": "segment", "operator": "equals", "value": "Enterprise"},
                        {
                            "any": [
                                {"column": "region", "operator": "equals", "value": "APAC"},
                                {"column": "overall_sat", "operator": "gte", "value": 7},
                            ]
                        },
                    ]
                },
            }
        ]

        normalized = normalize_segment_definitions(segments, df)
        previews = preview_segments(df, normalized)

        self.assertEqual(normalized[0]["name"], "Enterprise APAC or high sat")
        self.assertEqual(previews[0]["matched_count"], 2)
        self.assertEqual(previews[0]["matched_pct"], 50.0)
        self.assertEqual(previews[0]["warnings"], [])

    def test_rejects_duplicate_segment_names(self):
        df = pd.DataFrame({"segment": ["SMB", "Enterprise"]})
        segments = [
            {"name": "Enterprise", "tree": {"all": [{"column": "segment", "operator": "equals", "value": "Enterprise"}]}},
            {"name": " enterprise ", "tree": {"all": [{"column": "segment", "operator": "equals", "value": "SMB"}]}} ,
        ]

        with self.assertRaises(ValueError):
            normalize_segment_definitions(segments, df)

    def test_rejects_numeric_operator_on_text_column(self):
        df = pd.DataFrame({"segment": ["SMB", "Enterprise"]})
        segments = [
            {"name": "Bad numeric", "tree": {"all": [{"column": "segment", "operator": "gt", "value": 5}]}}
        ]

        with self.assertRaises(ValueError):
            normalize_segment_definitions(segments, df)

    def test_preview_flags_zero_and_all_match_segments(self):
        df = pd.DataFrame({"segment": ["SMB", "Enterprise", "Enterprise"]})
        segments = [
            {"name": "Nobody", "tree": {"all": [{"column": "segment", "operator": "equals", "value": "Mid-Market"}]}},
            {"name": "Everybody", "tree": {"all": [{"column": "segment", "operator": "not_null"}]}} ,
        ]

        previews = preview_segments(df, segments)
        self.assertIn("zero_matches", previews[0]["warnings"])
        self.assertIn("all_rows_match", previews[1]["warnings"])
        self.assertIn("nearly_everyone_matches", previews[1]["warnings"])


if __name__ == "__main__":
    unittest.main()
