"""Generate deployment manifests from historical profiles only; no runtime hooks."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from run_experiments import METHODS, BUDGETS, select


def load_history(path):
    projects = defaultdict(list)
    keys = set()
    with open(path, newline='', encoding='utf-8-sig') as f:
        for d in csv.DictReader(f):
            project = d['project']
            location = d['source_location']
            spec = d['monitor_specification']
            key = (project, location, spec)
            if key in keys:
                raise ValueError(f'Duplicate candidate: {key}')
            keys.add(key)
            cost = int(d['cost_proxy_event_checks'])
            if cost <= 0:
                raise ValueError(f'Nonpositive cost: {key}')
            ident = hashlib.sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()
            projects[project].append(dict(id=ident, location=location, spec=spec,
                assumed_location_id=d['creation_location_id_assumed'],
                frequency=int(d['monitor_frequency']), cost=cost,
                traces=frozenset(x.strip() for x in d['trace_ids'].split('|') if x.strip())))
    if not projects:
        raise ValueError('Empty historical profile')
    return projects


def generate(history, output, random_trials=5):
    if random_trials < 1:
        raise ValueError('random_trials must be positive')
    data = load_history(history)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(Path(history).read_bytes()).hexdigest()
    index = []
    for project, rows in sorted(data.items()):
        rows.sort(key=lambda a: a['id'])
        total = sum(a['cost'] for a in rows)
        registry = [{k: a[k] for k in ('id','location','spec','assumed_location_id','cost')} for a in rows]
        configs = [('none', 0, 0, []), ('full', 100, 0, rows)]
        for pct in BUDGETS:
            for method in METHODS:
                for trial in range(random_trials if method == 'random' else 1):
                    chosen = select(rows, total * pct // 100, method, seed=42+trial)
                    configs.append((method, pct, trial, chosen))
        for method, pct, trial, chosen in configs:
            used = sum(a['cost'] for a in chosen)
            if used > total * pct // 100:
                raise AssertionError('Proxy budget exceeded')
            ids = sorted(a['id'] for a in chosen)
            if len(ids) != len(set(ids)):
                raise AssertionError('Duplicate selection')
            config_id = f'{project}__{method}__{pct}__{trial}'
            manifest = dict(schema_version=1, config_id=config_id, project=project,
                algorithm=method, budget_pct=pct, trial=trial, seed=42+trial,
                history_sha256=digest, proxy_cost=used, proxy_total=total,
                mapping_status='unverified', selected_ids=ids,
                selected_candidates=[a for a in registry if a['id'] in set(ids)])
            filename = config_id + '.json'
            (output / filename).write_text(json.dumps(manifest, indent=2)+'\n')
            index.append(dict(config_id=config_id, project=project, algorithm=method,
                budget_pct=pct, trial=trial, proxy_cost=used, proxy_total=total,
                selected_count=len(ids), manifest=filename))
        (output / f'{project}__registry.json').write_text(json.dumps(registry, indent=2)+'\n')
    with (output / 'manifest_index.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(index[0]))
        writer.writeheader()
        writer.writerows(index)
    return index


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history', default='data/valg_profiles/monitor_profile.csv')
    p.add_argument('--output', default='results/online/manifests')
    p.add_argument('--random-trials', type=int, default=5)
    a = p.parse_args()
    print(f'Generated {len(generate(a.history, a.output, a.random_trials))} configurations')
