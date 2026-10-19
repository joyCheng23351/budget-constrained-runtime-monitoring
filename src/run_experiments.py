"""Offline monitor selection, not runtime instrumentation. Requires artifact_tool and matplotlib."""
import csv, random, json, math, argparse
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev
from artifact_tool import Blob, SpreadsheetFile

METHODS=['random','frequency','utility_cost','redundancy_greedy','knapsack_additive']
BUDGETS=[10,20,30,50,80]

def load(path):
    wb=SpreadsheetFile.import_xlsx(Blob.load(str(path)))
    sh=wb.worksheets.get_item('Monitor profile')
    rows=sh.get_range('A1:P220').values
    names=rows[0]; out=defaultdict(list)
    for row in rows[1:]:
        if not row[0]:continue
        d=dict(zip(names,row)); p=str(d['project']); traces=frozenset(x.strip() for x in str(d['trace_ids'] or '').split('|') if x.strip())
        out[p].append(dict(id=f'{p}:{len(out[p]):04d}',location=str(d['source_location']),spec=str(d['monitor_specification']),frequency=int(d['monitor_frequency']),cost=int(d['cost_proxy_event_checks']),traces=traces))
    return out

def cover(selected):
    x=set()
    for a in selected:x.update(a['traces'])
    return x

def select(rows,budget,method,seed=42,scale=1000):
    remaining=list(rows); chosen=[]; used=0
    if method=='random':
        random.Random(seed).shuffle(remaining)
    elif method=='frequency':
        remaining.sort(key=lambda a:(-a['frequency'],a['id']))
    elif method=='utility_cost':
        remaining.sort(key=lambda a:(-len(a['traces'])/a['cost'],-len(a['traces']),a['id']))
    elif method=='knapsack_additive':
        # Discretize costs upward; bounded runtime, optimistic? conservative feasibility.
        # unit derived from total cost / 1500; ceiling <= budget in true units.
        unit=max(1,math.ceil(sum(a['cost'] for a in rows)/scale))
        capacity=int(budget//unit)
        dp=[(0,()) for _ in range(capacity+1)]
        for j,a in enumerate(rows):
            c=math.ceil(a['cost']/unit)
            if c>capacity:continue
            for b in range(capacity,c-1,-1):
                candidate=dp[b-c][0]+len(a['traces'])
                if candidate>dp[b][0]:dp[b]=(candidate,dp[b-c][1]+(j,))
        best=max(dp,key=lambda e:e[0]); chosen=[rows[i] for i in best[1]]
        return chosen
    elif method=='redundancy_greedy':
        existing=set()
        while True:
            candidates=[a for a in remaining if used+a['cost']<=budget and len(a['traces']-existing)>0]
            if not candidates:break
            a=max(candidates,key=lambda x:(len(x['traces']-existing)/x['cost'],len(x['traces']-existing),-x['cost']))
            chosen.append(a);remaining.remove(a);used+=a['cost'];existing.update(a['traces'])
        return chosen
    for a in remaining:
        if used+a['cost']<=budget:
            chosen.append(a);used+=a['cost']
    return chosen

def save_csv(path, data):
    if not data:return
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',default='../valg-algorithm-input.xlsx');ap.add_argument('--output',default='results');ap.add_argument('--random-trials',type=int,default=30)
    args=ap.parse_args(); dest=Path(args.output);dest.mkdir(parents=True,exist_ok=True)
    data=load(Path(args.input));metric_rows=[];selection_rows=[];summary=[]
    for project,rows in data.items():
        assert all(a['cost']>0 for a in rows)
        universe=cover(rows);total=sum(a['cost'] for a in rows)
        summary.append({'project':project,'groups':len(rows),'trace_universe':len(universe),'total_proxy_cost':total,'violations_attributed':False})
        for pct in BUDGETS:
            budget=total*pct/100
            for algo in METHODS:
                for trial in range(args.random_trials if algo=='random' else 1):
                    chosen=select(rows,budget,algo,seed=42+trial)
                    cov=cover(chosen);cost=sum(a['cost'] for a in chosen)
                    assert cost<=budget+1e-6
                    assert cov.issubset(universe)
                    metric_rows.append(dict(project=project,budget_pct=pct,algorithm=algo,trial=trial,trace_recall=len(cov)/len(universe),trace_count=len(cov),monitor_count=len(chosen),proxy_cost=cost,proxy_budget=budget,proxy_cost_pct=100*cost/total))
                    selection_rows.append(dict(project=project,budget_pct=pct,algorithm=algo,trial=trial,selected_ids='|'.join(a['id'] for a in chosen)))
    save_csv(dest/'metrics_raw.csv',metric_rows);save_csv(dest/'selections.csv',selection_rows)
    aggregates=[]
    for project in data:
      for pct in BUDGETS:
       for algo in METHODS:
        subset=[a for a in metric_rows if (a['project'],a['budget_pct'],a['algorithm'])==(project,pct,algo)]
        recalls=[a['trace_recall'] for a in subset]
        aggregates.append(dict(project=project,budget_pct=pct,algorithm=algo,mean_trace_recall=mean(recalls),sd_trace_recall=stdev(recalls) if len(recalls)>1 else 0,mean_proxy_cost=mean(a['proxy_cost'] for a in subset),mean_selected_groups=mean(a['monitor_count'] for a in subset),trials=len(recalls)))
    save_csv(dest/'metrics_summary.csv',aggregates)
    with open(dest/'dataset_summary.json','w') as f:json.dump(summary,f,indent=2)
    try:
     import matplotlib;matplotlib.use('Agg')
     import matplotlib.pyplot as plt
     for project in data:
      fig,ax=plt.subplots(figsize=(8,5))
      for algo in METHODS:
       subset=[x for x in aggregates if x['project']==project and x['algorithm']==algo]
       ax.plot([x['budget_pct'] for x in subset],[100*x['mean_trace_recall'] for x in subset],marker='o',label=algo)
      ax.set(title=f'{project}: unique trace recall under proxy budgets',xlabel='Event-check proxy budget (% of full proxy)',ylabel='Unique trace recall (%)',ylim=(0,102));ax.grid(alpha=.25);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(dest/f'{project}_trace_recall.png',dpi=180);plt.close(fig)
    except ImportError:pass
    for a in aggregates:
     print(f"{a['project']:11} {a['budget_pct']:2}% {a['algorithm']:20} recall={a['mean_trace_recall']:.3f} sd={a['sd_trace_recall']:.3f}")

if __name__=='__main__':main()
