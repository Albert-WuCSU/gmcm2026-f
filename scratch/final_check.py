import io, re, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

tex = io.open('paper/sections/problem1.tex', encoding='utf-8').read()
i = tex.index(r'\label{tab:q1-mixture}')
a = tex.rindex(r'\begin{table}', 0, i)
b = tex.index(r'\end{table}', i)
tab = tex[a:b]
parta = tab[tab.index('(a)'):tab.index('(b)')]
partb = tab[tab.index('(b)'):]

m0 = json.load(io.open('results/Q1/experiments/round1/metrics/q1_mixture_M0c.json', encoding='utf-8'))
m1 = json.load(io.open('results/Q1/experiments/round1/metrics/q1_mixture_M1c.json', encoding='utf-8'))

bad = []
for scale, lab in [('test_1m', '1m'), ('test_60m', '60m'), ('test_1B', '1B')]:
    row = [l for l in partb.split('\n') if l.strip().startswith(lab + ' ') and '&' in l][0]
    q = m0['q_increment_test']['by_scale'][scale]
    for key in ['increment', 'p_only_r2_deoffset', 'p_plus_Q_r2_deoffset']:
        fmt = '%.5f' if key == 'increment' else '%.4f'
        if (fmt % q[key]) not in row:
            bad.append('%s %s want %s' % (scale, key, fmt % q[key]))
    print(lab, '->', row.strip())
print('part (b) vs JSON ->', 'OK' if not bad else bad)

bad = []
for scale, lab in [('test_1m', '1m'), ('test_60m', '60m'), ('test_1B', '1B')]:
    row = [l for l in parta.split('\n') if l.strip().startswith(lab + ' ') and '&' in l][0]
    v0 = m0['validation_by_scale'][scale]
    v1 = m1['validation_by_scale'][scale]
    for fmt, val, nm in [('%.4f', v0['r2_after_offset_removal'], 'M0c r2'),
                         ('%.4f', v1['r2_after_offset_removal'], 'M1c r2'),
                         ('%.3f', v0['r2_raw'], 'raw r2')]:
        if (fmt % val) not in row:
            bad.append('%s %s want %s' % (scale, nm, fmt % val))
print('part (a) vs JSON ->', 'OK' if not bad else bad)

print()
print('--- remaining half-width punctuation outside math/tabular/control-seq ---')


def is_math_ctx(s, i):
    return s[i - 1] == '$' or s[i + 1] == '$' or s[i - 1] == '\\'


left = []
for m in re.finditer(r'[,;:]', tex):
    p = m.start()
    prev = tex[p - 1] if p else ''
    nxt = tex[p + 1] if p + 1 < len(tex) else ''
    if prev == '\\' or prev == '$' or nxt == '$':
        continue
    left.append(tex[max(0, p - 28):p + 28].replace('\n', ' '))
print('count:', len(left))
for l in left:
    print('  ', l)
