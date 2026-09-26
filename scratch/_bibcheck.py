import re, glob, os
D = r'D:/Users/luqianwu/Desktop/华为杯/paper'
bib = open(D + '/reference.bib', encoding='utf-8').read()
keys = set(re.findall(r'@\w+\{([^,]+),', bib))
CITE = re.compile(r'\\cite[a-z]*\{([^}]*)\}')
used_all = set()
for f in sorted(glob.glob(D + '/sections/*.tex')):
    t = open(f, encoding='utf-8').read()
    used = set()
    for grp in CITE.findall(t):
        for p in grp.split(','):
            used.add(p.strip())
    used_all |= used
    miss = sorted(used - keys)
    print(os.path.basename(f), '| cites', len(used), '| MISSING:', miss if miss else 'none')
print()
print('bib entries:', len(keys))
print('unused entries:', sorted(keys - used_all))
print('cited but absent:', sorted(used_all - keys))
