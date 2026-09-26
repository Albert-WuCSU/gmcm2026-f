import io, difflib, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

old = io.open('scratch/problem1.tex.bak', encoding='utf-8').read()
new = io.open('paper/sections/problem1.tex', encoding='utf-8').read()

MAP = {',': '，', ';': '；', ':': '：', '(': '（', ')': '）'}
INV = {v: k for k, v in MAP.items()}


def canon(s):
    """drop all whitespace and unify punctuation width -> text-identity check"""
    s = ''.join(INV.get(c, c) for c in s)
    return re.sub(r'\s+', '', s)


sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
unexplained = []
punct_chunks = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        continue
    o = canon(old[i1:i2])
    n = canon(new[j1:j2])
    if o == n:
        punct_chunks += 1
    else:
        unexplained.append((tag, old[i1:i2], new[j1:j2]))

print('chunks differing only in whitespace/punctuation width : %d' % punct_chunks)
print('chunks with textual differences                      : %d' % len(unexplained))
print()
for tag, o, n in unexplained:
    print('=== %s' % tag)
    print('  OLD:', repr(o[:400]))
    print('  NEW:', repr(n[:400]))
    print()
