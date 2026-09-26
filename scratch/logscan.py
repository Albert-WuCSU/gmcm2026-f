import io, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = sys.argv[1]
t = io.open(p, encoding='utf-8', errors='replace').read()
pats = [r'^!', r'Runaway', r'File ended', r'Undefined control', r'LaTeX Warning: Reference',
        r'LaTeX Warning: Citation', r'LaTeX Warning: There were undefined',
        r'no output', r'Output written', r'\\@writefile']
out = []
for i, l in enumerate(t.split('\n')):
    for pt in pats:
        if re.search(pt, l):
            out.append(l.strip())
            break
print('--- matched lines (%d) ---' % len(out))
for l in out[:60]:
    print(l)
print()
print('--- last 25 lines ---')
tail = t.split('\n')[-25:]
for l in tail:
    print(l)
