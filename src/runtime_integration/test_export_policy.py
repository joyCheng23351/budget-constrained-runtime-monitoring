import csv
import tempfile
import unittest
from pathlib import Path

from export_policy import export_policy, stable_location


class ExportPolicyTest(unittest.TestCase):
    def test_stable_location_removes_identity_suffix(self):
        self.assertEqual("a.B(B.java:9)", stable_location("a.B.m(B.java:9)321"))

    def test_exports_selected_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.csv"
            selections = root / "selections.csv"
            output = root / "policy.tsv"
            with profile.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["project", "monitor_specification", "source_location"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "project": "demo",
                        "monitor_specification": "SpecMonitor",
                        "source_location": "a.B.m(B.java:9)321",
                    }
                )
            with selections.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["project", "budget_pct", "algorithm", "trial", "selected_ids"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "project": "demo",
                        "budget_pct": 20,
                        "algorithm": "frequency",
                        "trial": 0,
                        "selected_ids": "demo:0000",
                    }
                )
            manifest = export_policy(profile, selections, output, "demo", 20, "frequency", 0)
            self.assertEqual(1, manifest["unique_runtime_keys"])
            self.assertIn("SpecMonitor\ta.B(B.java:9)", output.read_text())


if __name__ == "__main__":
    unittest.main()
