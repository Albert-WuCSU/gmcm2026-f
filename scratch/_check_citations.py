"""Check that every \\cite key used in the paper exists in reference.bib."""
import pathlib
import re

used = {}
for f in sorted(pathlib.Path('paper/sections').glob('*.tex')):
    t = f.read_text(encoding='utf-8')
    for m in re.finditer(r'\\cite[a-zA-Z]*\{([^}]*)\}', t):
        for k in m.group(1).split(','):
            k = k.strip()
            if k:
                used.setdefault(k, []).append(f.name)

bib = pathlib.Path('paper/reference.bib').read_text(encoding='utf-8')
have = set(re.findall(r'@\w+\{([^,]+),', bib))

print('keys used :', len(used))
print('keys in bib:', len(have))
print()
print('MISSING from bib :', sorted(set(used) - have) or 'none')
print('UNUSED in bib    :', sorted(have - set(used)) or 'none')
print()
for k in sorted(used):
    print(f'  {k:<28} {",".join(sorted(set(used[k])))}')
