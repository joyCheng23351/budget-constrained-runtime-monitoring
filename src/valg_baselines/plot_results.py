#!/usr/bin/env python3
"""Aggregate compact Valg subset results and generate the report figure."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'results' / 'valg_baselines' / 'raw'
SUMMARY = ROOT / 'results' / 'valg_baselines' / 'summary'
FIGURES = ROOT / 'results' / 'valg_baselines' / 'figures'


def load_rows():
    rows = []
    for path in sorted(RAW.glob('*-summary.csv')):
        with path.open(newline='') as stream:
            rows.extend(csv.DictReader(stream))
    return rows


def number(row, key):
    value = row.get(key, '')
    return float(value) if value not in ('', None) else None


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = load_rows()
    by_project = {}
    for row in rows:
        by_project.setdefault(row['project'], {})[row['mode']] = row

    runtime = []
    trace = []
    for project in sorted(by_project):
        modes = by_project[project]
        no_rv = number(modes.get('no-RV', {}), 'duration_ms')
        valgj = number(modes.get('ValgJ', {}), 'duration_ms')
        javamop = number(modes.get('JavaMOP', {}), 'duration_ms')
        runtime.append({
            'project': project,
            'no_rv_seconds': no_rv / 1000 if no_rv else '',
            'valgj_seconds': valgj / 1000 if valgj else '',
            'javamop_seconds': javamop / 1000 if javamop else '',
            'valgj_vs_javamop_time_reduction':
                (javamop - valgj) / javamop if valgj and javamop else '',
            'valgj_unique_violation_rows': modes.get('ValgJ', {}).get('unique_violation_rows', ''),
            'javamop_unique_violation_rows': modes.get('JavaMOP', {}).get('unique_violation_rows', ''),
        })

        valgt = modes.get('ValgT', {})
        tracemop = modes.get('TraceMOP', {})
        if valgt.get('status') == 'success' and tracemop.get('status') == 'success':
            vu = number(valgt, 'unique_traces')
            tu = number(tracemop, 'unique_traces')
            vd = number(valgt, 'derived_duplicate_trace_instances')
            td = number(tracemop, 'derived_duplicate_trace_instances')
            vt = number(valgt, 'duration_ms')
            tt = number(tracemop, 'duration_ms')
            trace.append({
                'project': project,
                'valgt_seconds': vt / 1000,
                'tracemop_seconds': tt / 1000,
                'time_reduction': (tt - vt) / tt,
                'valgt_unique_traces': int(vu),
                'tracemop_unique_traces': int(tu),
                'unique_trace_retention': vu / tu,
                'valgt_duplicate_instances': int(vd),
                'tracemop_duplicate_instances': int(td),
                'duplicate_instance_reduction': (td - vd) / td,
            })

    write_csv(SUMMARY / 'runtime_comparison.csv', runtime, list(runtime[0]))
    write_csv(SUMMARY / 'trace_comparison.csv', trace, list(trace[0]))

    from PIL import Image, ImageDraw, ImageFont
    from math import log10

    FIGURES.mkdir(parents=True, exist_ok=True)
    image = Image.new('RGB', (2400, 1000), 'white')
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 34)
    small = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 29)
    bold = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 42)
    colors = {'no-RV': '#9CA3AF', 'ValgJ': '#4C78A8', 'JavaMOP': '#F58518',
              'ValgT': '#7A5195', 'TraceMOP': '#EF5675'}

    def axes(left, top, right, bottom, title, ylabel):
        draw.line((left, top, left, bottom), fill='#333333', width=3)
        draw.line((left, bottom, right, bottom), fill='#333333', width=3)
        draw.text((left, top-64), title, font=bold, fill='#111111')
        draw.text((left, top-20), ylabel, font=small, fill='#555555')

    # Panel A: measured end-to-end runtimes.
    left, top, right, bottom = 120, 140, 1170, 820
    axes(left, top, right, bottom, 'Java-mode artifact runs', 'End-to-end time (s)')
    max_time = max(r['javamop_seconds'] for r in runtime) * 1.08
    group_w = (right-left) / len(runtime)
    bar_w = 58
    for i, row in enumerate(runtime):
        center = left + group_w*(i+.5)
        for j, mode in enumerate(('no-RV', 'ValgJ', 'JavaMOP')):
            value = row[{'no-RV':'no_rv_seconds','ValgJ':'valgj_seconds','JavaMOP':'javamop_seconds'}[mode]]
            x0 = center + (j-1)*bar_w - bar_w*.42
            y0 = bottom - (value/max_time)*(bottom-top)
            draw.rectangle((x0, y0, x0+bar_w*.84, bottom), fill=colors[mode])
        label = row['project'].replace('route53-infima', 'route53')
        box = draw.textbbox((0,0), label, font=small)
        draw.text((center-(box[2]-box[0])/2, bottom+18), label, font=small, fill='#222222')
    for j, mode in enumerate(('no-RV', 'ValgJ', 'JavaMOP')):
        x0 = left + j*210
        draw.rectangle((x0, 895, x0+34, 929), fill=colors[mode])
        draw.text((x0+46, 892), mode, font=small, fill='#222222')

    # Panel B: complete trace pair on a base-10 log scale.
    t = trace[0]
    left, top, right, bottom = 1320, 140, 2290, 820
    axes(left, top, right, bottom, f"Trace-mode pair: {t['project']}", 'Count (base-10 log scale)')
    categories = [('Unique traces', t['valgt_unique_traces'], t['tracemop_unique_traces']),
                  ('Duplicate instances', t['valgt_duplicate_instances'], t['tracemop_duplicate_instances'])]
    max_log = max(log10(v) for _, a, b in categories for v in (a,b)) * 1.05
    for i, (label, valgt_value, full_value) in enumerate(categories):
        center = left + (right-left)*(i+.5)/2
        for offset, mode, value in ((-70, 'ValgT', valgt_value), (20, 'TraceMOP', full_value)):
            y0 = bottom - (log10(value)/max_log)*(bottom-top)
            draw.rectangle((center+offset, y0, center+offset+70, bottom), fill=colors[mode])
        box = draw.textbbox((0,0), label, font=small)
        draw.text((center-(box[2]-box[0])/2, bottom+18), label, font=small, fill='#222222')
    for j, mode in enumerate(('ValgT', 'TraceMOP')):
        x0 = left + j*220
        draw.rectangle((x0, 895, x0+34, 929), fill=colors[mode])
        draw.text((x0+46, 892), mode, font=small, fill='#222222')
    image.save(FIGURES / 'valg_subset_summary.png')


if __name__ == '__main__':
    main()
