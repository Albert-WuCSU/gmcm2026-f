import io, re, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = 'paper/sections/problem1.tex'
APPLY = '--apply' in sys.argv
t = io.open(PATH, encoding='utf-8', newline='').read()
n = len(t)
prot = [False] * n
in_tab = [False] * n


def mask(a, b):
    for k in range(max(0, a), min(b, n)):
        prot[k] = True


# inline math
dollars = [m.start() for m in re.finditer(r'(?<!\\)\$', t)]
for a, b in zip(dollars[0::2], dollars[1::2]):
    mask(a, b + 1)

# math environments
for env in ['equation', 'equation*', 'align', 'align*', 'gather', 'array']:
    for m in re.finditer(r'\\begin\{' + re.escape(env) + r'\}', t):
        e = t.find(r'\end{' + env + '}', m.end())
        mask(m.start(), (e + len(env) + 6) if e != -1 else n)

# tabular: numeric cells must keep half-width punctuation -> convert only CJK-adjacent
for m in re.finditer(r'\\begin\{tabular\}', t):
    e = t.find(r'\end{tabular}', m.end())
    end = (e + 12) if e != -1 else n
    for k in range(m.start(), end):
        in_tab[k] = True

# protected command arguments
PROT_CMDS = r'label|ref|eqref|citep|citet|cite|includegraphics|texttt|textbf|textit|begin|end|input|url'
for m in re.finditer(r'\\(' + PROT_CMDS + r')\s*\{', t):
    dep, k = 0, m.end() - 1
    while k < n:
        if t[k] == '{':
            dep += 1
        elif t[k] == '}':
            dep -= 1
            if dep == 0:
                break
        k += 1
    mask(m.start(), k + 1)

# panel labels (a)-(d) stay half-width, as in the other sections
for m in re.finditer(r'\([a-d]\)', t):
    mask(m.start(), m.end())

MAP = {',': '\uff0c', ';': '\uff1b', ':': '\uff1a', '(': '\uff08', ')': '\uff09'}


def cjk(c):
    return c != '' and ('\u3000' <= c <= '\u9fff' or c in '\uff0c\u3002\uff1b\uff1a\u3001\uff08\uff09\u300c\u300d\uff0e')


out = list(t)
stats = {}
skipped = []
kept = []
for i, c in enumerate(t):
    if c not in MAP or prot[i]:
        continue
    prev = t[i - 1] if i else ''
    nxt = t[i + 1] if i + 1 < n else ''
    if prev == '\\':
        skipped.append(t[max(0, i - 30):i + 30].replace('\n', ' '))
        continue
    adj = cjk(prev) or cjk(nxt)
    if in_tab[i] and not adj:
        kept.append(t[max(0, i - 30):i + 30].replace('\n', ' '))
        continue
    out[i] = MAP[c]
    stats[c] = stats.get(c, 0) + 1

print('converted:', {k: v for k, v in sorted(stats.items())})
print('kept inside tabular (numeric):', len(kept))
print('skipped control-seq:', len(skipped))

if APPLY:
    io.open(PATH, 'w', encoding='utf-8', newline='').write(''.join(out))
    print('WRITTEN')
