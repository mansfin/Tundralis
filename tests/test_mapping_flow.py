import json
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "test-artifacts"


class TestMappingFlow(unittest.TestCase):
    def test_mapping_config_fixture_flow(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        json_path = OUTPUT_DIR / "client_style_analysis_run.json"
        pptx_path = OUTPUT_DIR / "client_style_report.pptx"

        cmd = [
            str(ROOT / ".venv" / "bin" / "python"),
            str(ROOT / "tundralis_kda.py"),
            "--data", str(ROOT / "data" / "fixtures" / "client_style_kda.csv"),
            "--mapping-config", str(ROOT / "data" / "fixtures" / "client_style_kda_mapping.json"),
            "--no-ai",
            "--json-output", str(json_path),
            "--output", str(pptx_path),
        ]
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(json_path.read_text())
        self.assertEqual(payload["input_summary"]["target_column"], "overall_sat")
        self.assertEqual(len(payload["input_summary"]["segment_columns"]), 2)
        self.assertEqual(len(payload["drivers"]), 10)
        self.assertGreater(payload["input_summary"]["rows_with_valid_dv_and_any_predictor"], 0)


if __name__ == "__main__":
    unittest.main()
