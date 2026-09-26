import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
s = open('paper/sections/problem3.tex', encoding='utf-8').read()

# split into tabular environments
for m in re.finditer(r'\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}', s, re.S):
    spec = m.group(1)
    body = m.group(2)
    ncols = len(re.findall(r'[lcr]|p\{[^}]*\}', spec))
    rows = [r for r in body.split('\\\\')]
    print('--- tabular spec:', spec, '=> declared cols:', ncols)
    for r in rows:
        r2 = re.sub(r'\\(toprule|midrule|bottomrule|cmidrule\{[^}]*\})', '', r).strip()
        r2 = re.sub(r'\\hline', '', r2).strip()
        if not r2:
            continue
        # remove braces content? count & + 1, but nested braces with commas are fine; \& escaped not expected
        cells = len(re.findall(r'(?<!\\)&', r2)) + 1
        print('   cells:', cells, '|', r2[:70].replace('\n', ' '))
