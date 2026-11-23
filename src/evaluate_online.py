"""Evaluate paired fresh executions; never infer violations from selected groups."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev


def ids(value):
    result = json.loads(value)
    if not isinstance(result, list) or any(not isinstance(x, str) or not x for x in result):
        raise ValueError('Expected JSON array of nonempty canonical identifiers')
    return set(result)


def recall(observed, reference):
    return len(observed & reference) / len(reference) if reference else None


def evaluate(input_path, output, manifest_dir):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifests = {}
    with (Path(manifest_dir) / 'manifest_index.csv').open(newline='') as f:
        for row in csv.DictReader(f):
            m = json.loads((Path(manifest_dir) / row['manifest']).read_text())
            manifests[m['config_id']] = m
    runs = {}
    with open(input_path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            key = (row['project'], row['workload'], row['repeat'], row['config_id'])
            if key in runs:
                raise ValueError(f'Duplicate run: {key}')
            if row['status'] != 'ok':
                raise ValueError(f'Unsuccessful run; report and rerun before analysis: {key}')
            for field in ('wall_seconds', 'peak_rss_bytes'):
                v = float(row[field])
                if not math.isfinite(v) or v <= 0:
                    raise ValueError(f'Invalid {field}: {key}')
                row[field] = v
            if row['config_id'] not in ('valg',):
                m = manifests[row['config_id']]
                if m['project'] != row['project']:
                    raise ValueError(f'Manifest project mismatch: {key}')
                row.update(algorithm=m['algorithm'], budget_pct=m['budget_pct'], trial=m['trial'])
                if ids(row['enabled_ids']) != set(m['selected_ids']):
                    raise ValueError(f'Enabled candidates differ from requested set: {key}')
            else:
                row.update(algorithm='valg', budget_pct='', trial=0)
            row['traces'] = ids(row['trace_ids'])
            row['violations'] = ids(row['violation_ids']) if row['violation_ids'].strip() else None
            runs[key] = row
    if not runs:
        raise ValueError('No runtime measurements')
    raw = []
    for (project, workload, repeat, config), row in sorted(runs.items()):
        none = runs[(project, workload, repeat, f'{project}__none__0__0')]
        full = runs[(project, workload, repeat, f'{project}__full__100__0')]
        if none['traces'] or none['violations']:
            raise ValueError('No-monitor baseline emitted monitoring results')
        t, m = row['wall_seconds'], row['peak_rss_bytes']
        raw.append(dict(project=project, workload=workload, repeat=repeat, config_id=config,
            algorithm=row['algorithm'], budget_pct=row['budget_pct'], trial=row['trial'],
            wall_seconds=t, peak_rss_bytes=m,
            time_overhead_pct=100*(t/none['wall_seconds']-1),
            memory_overhead_pct=100*(m/none['peak_rss_bytes']-1),
            trace_recall=recall(row['traces'],full['traces']),
            violation_recall=recall(row['violations'], full['violations'])
                if row['violations'] is not None and full['violations'] is not None else None,
            unexpected_trace_ids=len(row['traces']-full['traces']),
            unexpected_violation_ids=len(row['violations']-full['violations'])
                if row['violations'] is not None and full['violations'] is not None else None))
    groups = defaultdict(list)
    for row in raw:
        groups[(row['project'],row['workload'],row['algorithm'],row['budget_pct'],row['trial'])].append(row)
    summary = []
    fields = ('wall_seconds','peak_rss_bytes','time_overhead_pct','memory_overhead_pct','trace_recall','violation_recall')
    for key, rows in groups.items():
        result = dict(zip(('project','workload','algorithm','budget_pct','trial'),key))
        result['repeats'] = len(rows)
        for field in fields:
            values = [r[field] for r in rows if r[field] is not None]
            result[field+'_n'] = len(values)
            result[field+'_mean'] = mean(values) if values else None
            result[field+'_sd'] = stdev(values) if len(values)>1 else None
        summary.append(result)
    for name, rows in [('metrics_raw.csv',raw),('metrics_summary.csv',summary)]:
        with (output/name).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    plot(summary, output)
    return summary


def plot(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups = defaultdict(list)
    for row in summary:
        groups[(row['project'],row['workload'])].append(row)
    for i, ((project, workload), rows) in enumerate(groups.items()):
        for cost in ('time_overhead_pct','memory_overhead_pct'):
            for metric in ('trace_recall','violation_recall'):
                fig, ax = plt.subplots(figsize=(8,5))
                for method in sorted({r['algorithm'] for r in rows}):
                    points = [r for r in rows if r['algorithm']==method and r[metric+'_mean'] is not None]
                    if not points:
                        continue
                    ax.errorbar([r[cost+'_mean'] for r in points],
                        [100*r[metric+'_mean'] for r in points],
                        xerr=[r[cost+'_sd'] or 0 for r in points],
                        yerr=[100*(r[metric+'_sd'] or 0) for r in points],
                        fmt='o', capsize=2, label=method)
                ax.set(xlabel=cost.replace('_',' '), ylabel=metric.replace('_',' ')+' (%)',
                       title=f'{project}: {workload}', ylim=(-3,103))
                if ax.has_data():
                    ax.legend(fontsize=8)
                    ax.grid(alpha=.25)
                    fig.tight_layout()
                    fig.savefig(output/f'{i}_{cost}_{metric}.png',dpi=180)
                plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--manifests', default='results/online/manifests')
    p.add_argument('--output', default='results/online/evaluation')
    a = p.parse_args()
    evaluate(a.input, a.output, a.manifests)
