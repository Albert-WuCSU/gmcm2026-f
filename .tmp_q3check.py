import re
p = 'paper/sections/problem3.tex'
s = open(p, encoding='utf-8').read()
pat = re.compile(r'\\begin\{tabular\}\{((?:[^{}]|\{[^{}]*\})*)\}(.*?)\\end\{tabular\}', re.S)
for i, m in enumerate(pat.finditer(s), 1):
    spec = m.group(1)
    clean = re.sub(r'p\{\s*[^{}]*\}', 'P', spec).replace('@{}', '')
    ncol = len(re.findall(r'[lcrP]', clean))
    body = re.sub(r'\\(toprule|midrule|bottomrule|hline)', '', m.group(2))
    counts = sorted({r.strip().count('&') + 1 for r in body.split('\\\\') if r.strip()})
    print('table %d %s declared=%d rows=%s  spec=%s' % (i, 'OK' if counts == [ncol] else '*** MISMATCH ***', ncol, counts, spec))
