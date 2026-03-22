import io
import unittest
from pathlib import Path

from tundralis.app import app

ROOT = Path(__file__).resolve().parents[1]


class TestWebMapping(unittest.TestCase):
    def test_inspect_renders_column_inspector(self):
        client = app.test_client()
        csv_bytes = (ROOT / "data" / "fixtures" / "client_style_kda.csv").read_bytes()

        response = client.post(
            "/inspect",
            data={"survey_file": (io.BytesIO(csv_bytes), "client_style_kda.csv")},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Column inspector", html)
        self.assertIn("Recode studio", html)
        self.assertIn("overall_sat", html)
        self.assertIn("high_cardinality", html)

    def test_preview_applies_recode_and_returns_segment_counts(self):
        client = app.test_client()
        csv_bytes = (ROOT / "data" / "fixtures" / "client_style_kda.csv").read_bytes()
        inspect_response = client.post(
            "/inspect",
            data={"survey_file": (io.BytesIO(csv_bytes), "client_style_kda.csv")},
            content_type="multipart/form-data",
        )
        html = inspect_response.get_data(as_text=True)
        marker = 'name="filename" value="'
        start = html.index(marker) + len(marker)
        filename = html[start: html.index('"', start)]

        response = client.post(
            "/preview",
            json={
                "filename": filename,
                "recode_definitions": [
                    {
                        "type": "map_values",
                        "source_column": "segment",
                        "output_column": "segment_group",
                        "mapping": {
                            "SMB": "Commercial",
                            "Mid-Market": "Commercial",
                            "Enterprise": "Enterprise",
                        },
                    }
                ],
                "segment_definitions": [
                    {
                        "name": "Enterprise only",
                        "tree": {
                            "all": [
                                {"column": "segment_group", "operator": "equals", "value": "Enterprise"}
                            ]
                        },
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("segment_group", payload["columns"])
        self.assertEqual(payload["segment_previews"][0]["name"], "Enterprise only")
        self.assertGreater(payload["segment_previews"][0]["matched_count"], 0)


if __name__ == "__main__":
    unittest.main()
