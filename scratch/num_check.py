import io, re, csv, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TEX = 'paper/sections/problem1.tex'
tex = io.open(TEX, encoding='utf-8').read()


def block(label):
    i = tex.index(r'\label{' + label + '}')
    a = tex.rindex(r'\begin{table}', 0, i)
    b = tex.index(r'\end{table}', i)
    return tex[a:b]


rows = list(csv.DictReader(io.open(
    'results/Q1/experiments/round1/tables/q1b_conflict_rates.csv', encoding='utf-8-sig')))
tab = block('tab:q1-conflict')
prefix = {'CD2': 'CD2', 'CD1': 'MAD', 'ge5': '至少五高',
          'ge3': '至少三高且至少三低'}
crit = {'CD2': 'CD2_high_value_and_high_pollution',
        'CD1': 'CD1_indicator_MAD_anchored',
        'ge5': 'CD3_ge5_high_and_ge5_low',
        'ge3': 'CD3_ge3_high_and_ge3_low'}
bad = []
for lab in ['CD2', 'CD1', 'ge5', 'ge3']:
    line = [l for l in tab.split('\n') if l.strip().startswith(prefix[lab])][0]
    shown = re.findall(r'0\.\d{4}', line)
    for idx, anc in enumerate(['p70', 'p75', 'p80']):
        src = [r for r in rows if r['population'] == 'pooled'
               and r['anchor'] == anc and r['criterion'] == crit[lab]][0]
        if abs(float(shown[idx]) - float(src['conflict_rate'])) > 5e-5:
            bad.append('%s@%s shown %s truth %s' % (lab, anc, shown[idx], src['conflict_rate']))
print('tab:q1-conflict (a) vs CSV ->', 'OK' if not bad else bad)

probe = json.load(io.open('workspace/data/q1_probe_conflict_by_domain.json', encoding='utf-8'))
cd2 = probe['by_anchor']['p75']['CD2']['by_domain']
cd1 = probe['by_anchor']['p75']['CD1']['by_domain']
ge3 = probe['by_anchor']['p75']['CD3_ge3']['by_domain']
bad = []
for d in ['stackexchange', 'wikipedia', 'arxiv', 'github', 'book', 'commoncrawl', 'c4']:
    line = [l for l in tab.split('\n') if l.strip().startswith(d)][0]
    shown = re.findall(r'0\.\d+', line)
    for got, truth, nm in zip(shown, [cd2[d], cd1[d], ge3[d]], ['CD2', 'CD1-fixed', 'ge3']):
        if abs(float(got) - truth) > 5e-4:
            bad.append('%s %s shown %s truth %.6f' % (d, nm, got, truth))
print('tab:q1-conflict (b) vs probe ->', 'OK' if not bad else bad)

# ---- tab:q1-domain-quality vs CSV
csvrows = list(csv.DictReader(io.open(
    'results/Q1/experiments/round1/tables/q1a_domain_quality.csv', encoding='utf-8-sig')))
tab = block('tab:q1-domain-quality')
bad = []
for r in csvrows:
    line = [l for l in tab.split('\n') if l.strip().startswith(r['domain'])]
    if not line:
        bad.append('row missing ' + r['domain'])
        continue
    l = line[0]
    for key in ['huber', 'ci95_lo', 'ci95_hi']:
        if ('%.4f' % float(r[key])) not in l:
            bad.append('%s %s want %.4f' % (r['domain'], key, float(r[key])))
    if ('%d' % int(r['n'])) not in l.replace(r'\,', ''):
        bad.append('%s n want %s' % (r['domain'], r['n']))
print('tab:q1-domain-quality vs CSV ->', 'OK' if not bad else bad)

# ---- tab:q1-mixture vs metrics JSON
m0 = json.load(io.open('results/Q1/experiments/round1/metrics/q1_mixture_M0c.json', encoding='utf-8'))
tab = block('tab:q1-mixture')
bad = []
for scale in ['test_1m', 'test_60m', 'test_1B']:
    row = [l for l in tab.split('\n') if l.strip().startswith(scale[5:]) and '&' in l][0]
    v = m0['validation_by_scale'][scale]
    if ('%.4f' % v['r2_after_offset_removal']) not in row:
        bad.append('%s r2 want %.4f' % (scale, v['r2_after_offset_removal']))
    if ('%.3f' % v['r2_raw']) not in row:
        bad.append('%s r2_raw want %.3f' % (scale, v['r2_raw']))
    q = m0['q_increment_test']['by_scale'][scale]
    if ('%.5f' % q['increment']) not in row:
        bad.append('%s increment want %.5f' % (scale, q['increment']))
print('tab:q1-mixture vs JSON ->', 'OK' if not bad else bad)

lo, hi = m0['q_increment_test']['by_scale']['test_1B']['increment_ci95']
print('1B CI truth (raw):        (%.8f, %.8f)' % (lo, hi))
print('1B row rendered in tex:  ',
      [l for l in tab.split('\n') if l.strip().startswith('1B') and '&' in l][0].strip())

print()
print('body  1.5e-5 occurrences :', tex.count(r'1.5\times10^{-5}'))
print('stale 0.00002 in tex     :', '0.00002' in tex)
print('stale 0.0091 in tex      :', '0.0091' in tex)
print('stale 三位有效数字        :', '三位有效数字' in tex)
print('half-width comma count   :', tex.count(','))
print('full-width comma count   :', tex.count('，'))
