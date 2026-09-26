import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

M1 = json.load(open('results/Q3/experiments/round1/metrics/q3_M1o.json', encoding='utf-8'))
M0 = json.load(open('results/Q3/experiments/round1/metrics/q3_M0o.json', encoding='utf-8'))

print('== sweep point at 22.625 ==')
for p in M1['sweep']['points']:
    if abs(p['log10_C'] - 22.625) < 1e-9:
        print(json.dumps(p, ensure_ascii=False, indent=1))
print('== share_order transitions in sweep ==')
prev = None
for p in M1['sweep']['points']:
    if p['share_order'] != prev:
        print('  ', p['log10_C'], p['share_order'], p['branch'])
        prev = p['share_order']
print('== branch transitions ==')
prev = None
for p in M1['sweep']['points']:
    if p['branch'] != prev:
        print('  ', p['log10_C'], p['branch'], p['Q'])
        prev = p['branch']

print('== M0o top-level keys ==')
print(list(M0.keys()))
for k in M0.keys():
    if k in ('anchors', 'baseline_by_budget'):
        continue
    print('=== '+k+' ===')
    print(json.dumps(M0[k], ensure_ascii=False, indent=1)[:3000])
