import io, sys, re, glob, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

p = 'paper/sections/problem3.tex'
s = open(p, encoding='utf-8').read()

print('braces { }:', s.count('{'), s.count('}'))
print('begin:', re.findall(r'\\begin\{(\w+)\}', s))
print('end:', re.findall(r'\\end\{(\w+)\}', s))
print('usepackage:', 'usepackage' in s)
print('[H]:', '[H]' in s)
print('includegraphics:', re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}', s))
print('labels:', re.findall(r'\\label\{([^}]*)\}', s))
print('refs:', re.findall(r'\\(?:ref|eqref|autoref)\{([^}]*)\}', s))
print('cites:', re.findall(r'\\cite[tp]?\{([^}]*)\}', s))
print('tabular spec rows:')
for m in re.finditer(r'\\begin\{tabular\}\{([^}]*)\}', s):
    print('   ', m.group(1))

# global label inventory in the paper tree (excluding .git)
allbl = {}
for f in glob.glob('paper/**/*.tex', recursive=True):
    if '.git' in f:
        continue
    t = open(f, encoding='utf-8', errors='replace').read()
    for lb in re.findall(r'\\label\{([^}]*)\}', t):
        allbl.setdefault(lb, []).append(f)

refs = re.findall(r'\\(?:ref|eqref)\{([^}]*)\}', s)
print('--- ref resolution ---')
for r in sorted(set(refs)):
    n = len(allbl.get(r, []))
    print('  ', r, '=> defs:', n, allbl.get(r, [])[:3])

dups = {k: v for k, v in allbl.items() if len(v) > 1}
print('--- duplicate labels ---')
for k, v in dups.items():
    print('  ', k, v)

# bib keys
bibf = [f for f in glob.glob('paper/**/*.bib', recursive=True) if '.git' not in f]
print('bib files:', bibf)
keys = set()
for f in bibf:
    t = open(f, encoding='utf-8', errors='replace').read()
    keys |= set(re.findall(r'@\w+\{([^,]+),', t))
print('--- citation key resolution ---')
for c in sorted(set(x.strip() for grp in re.findall(r'\\cite[tp]?\{([^}]*)\}', s) for x in grp.split(','))):
    print('  ', c, 'in bib:', c in keys)
