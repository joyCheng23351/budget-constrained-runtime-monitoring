"""Synthetic smoke test only. Does not produce research measurements."""
import csv
import json
import math
import tempfile
import unittest
from pathlib import Path

from evaluate_online import evaluate, recall

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / 'results/online/manifests'


class EvaluationTest(unittest.TestCase):
    def test_pipeline(self):
        project = 'javadbf'
        configs = [
            (f'{project}__none__0__0', 10, 100, [], []),
            (f'{project}__full__100__0', 20, 200, ['t1','t2','t3','t4'], ['v1','v2']),
            (f'{project}__utility_cost__20__0', 12, 125, ['t1','t2','t3','extra'], ['v1']),
            ('valg', 15, 150, ['t1','t2'], None),
        ]
        rows = []
        for repeat in (1, 2):
            for config, wall, rss, traces, violations in configs:
                enabled = [] if config == 'valg' else json.loads(
                    (MANIFESTS / (config + '.json')).read_text())['selected_ids']
                rows.append(dict(project=project, workload='synthetic_only', repeat=repeat,
                    config_id=config, status='ok', wall_seconds=wall,
                    peak_rss_bytes=rss, enabled_ids=json.dumps(enabled),
                    trace_ids=json.dumps(traces),
                    violation_ids=json.dumps(violations) if violations is not None else ''))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            def write():
                with (p/'runs.csv').open('w', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
            write()
            summary = evaluate(p/'runs.csv', p/'out', MANIFESTS)
            by_method = {r['algorithm']:r for r in summary}
            selected = by_method['utility_cost']
            for field, expected in [('trace_recall_mean', .75), ('violation_recall_mean', .5),
                ('time_overhead_pct_mean', 20), ('memory_overhead_pct_mean', 25),
                ('trace_recall_sd', 0)]:
                self.assertTrue(math.isclose(selected[field], expected, abs_tol=1e-9))
            self.assertEqual(selected['repeats'], 2)
            self.assertIsNone(by_method['valg']['violation_recall_mean'])
            self.assertEqual(by_method['full']['trace_recall_mean'], 1)
            self.assertEqual(by_method['none']['trace_recall_mean'], 0)
            with (p/'out/metrics_raw.csv').open() as f:
                raw = list(csv.DictReader(f))
            self.assertEqual(len(raw), 8)
            self.assertTrue(all(int(r['unexpected_trace_ids']) == 1
                for r in raw if r['algorithm']=='utility_cost'))
            self.assertEqual(len(list((p/'out').glob('*.png'))), 4)
            # Negative test: enabled IDs must match the manifest.
            rows[2]['enabled_ids'] = json.dumps(['invalid'])
            write()
            with self.assertRaisesRegex(ValueError, 'Enabled candidates differ'):
                evaluate(p/'runs.csv', p/'out', MANIFESTS)

    def test_empty_reference(self):
        self.assertIsNone(recall({'t1'}, set()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
