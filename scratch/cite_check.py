import io, re, glob, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

bib = io.open('paper/reference.bib', encoding='utf-8').read()
keys = set(re.findall(r'@\w+\{([^,]+),', bib))

used = {}
for f in sorted(glob.glob('paper/sections/*.tex')) + sorted(glob.glob('paper/*.tex')):
    t = io.open(f, encoding='utf-8').read()
    for m in re.finditer(r'\\cite[pt]?\{([^}]*)\}', t):
        for k in m.group(1).split(','):
            k = k.strip()
            if k:
                used.setdefault(k, []).append(f)

missing = {k: v for k, v in used.items() if k not in keys}
unused = sorted(keys - set(used))
print('bib keys:', len(keys))
print('cited keys:', len(used))
print('UNDEFINED citations:', missing if missing else 'none')
print('uncited bib entries:', unused if unused else 'none')
