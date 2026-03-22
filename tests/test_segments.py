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


if __name__ == "__main__":
    unittest.main()
