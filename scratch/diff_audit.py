import io, difflib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

old = io.open('scratch/problem1.tex.bak', encoding='utf-8').read().split('\n')
new = io.open('paper/sections/problem1.tex', encoding='utf-8').read().split('\n')

PAIRS = {',': '，', ';': '；', ':': '：', '(': '（', ')': '）'}
INV = {v: k for k, v in PAIRS.items()}


def punct_only(a, b):
    """True if a and b become identical once punctuation width is normalised away."""
    for t in (a, b):
        pass

    def strip(s):
        return ' '.join(''.join(c for c in s if c not in set(PAIRS) | set(INV)).split())
    return strip(a) == strip(b)


sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
blocks = [b for b in sm.get_opcodes() if b[0] != 'equal']
punct_only_blocks = 0
content_blocks = []
for tag, i1, i2, j1, j2 in blocks:
    o = old[i1:i2]
    n = new[j1:j2]
    if len(o) == len(n) and all(punct_only(x, y) for x, y in zip(o, n)):
        punct_only_blocks += 1
        continue
    # allow the case where lines were merged / rewrapped but only punctuation differs
    oset = set()
    for l in o:
        oset.add(''.join(c for c in l if c not in set(PAIRS) | set(INV)).replace(' ', ''))
    nset = set()
    for l in n:
        nset.add(''.join(c for c in l if c not in set(PAIRS) | set(INV)).replace(' ', ''))
    if oset == nset:
        content_blocks.append(('REWRAP-only', o, n))
        continue
    content_blocks.append(('CONTENT', o, n))

print('diff blocks total          :', len(blocks))
print('punctuation-only blocks    :', punct_only_blocks)
print('other blocks               :', len(content_blocks))
print()
for kind, o, n in content_blocks:
    print('=== %s' % kind)
    for l in o:
        print('  -', l)
    for l in n:
        print('  +', l)
    print()
