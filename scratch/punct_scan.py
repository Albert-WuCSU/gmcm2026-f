import io, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PATH = 'paper/sections/problem1.tex'
t = io.open(PATH, encoding='utf-8').read()
n = len(t)
prot = [False] * n


def mask(a, b):
    for k in range(max(0, a), min(b, n)):
        prot[k] = True


# 1) inline math
dollars = [m.start() for m in re.finditer(r'(?<!\\)\$', t)]
for a, b in zip(dollars[0::2], dollars[1::2]):
    mask(a, b + 1)

# 2) math / numeric environments
for env in ['equation', 'equation*', 'align', 'align*', 'gather', 'array']:
    for m in re.finditer(r'\\begin\{' + re.escape(env) + r'\}', t):
        e = t.find(r'\end{' + env + '}', m.end())
        mask(m.start(), (e + len(env) + 6) if e != -1 else n)

# 3) protected command arguments
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

# 4) panel labels
for m in re.finditer(r'\([a-d]\)', t):
    mask(m.start(), m.end())


def cjk(c):
    return c != '' and ('\u3000' <= c <= '\u9fff' or c in '，。；：、（）「」．')


rows = []
for i, c in enumerate(t):
    if c in ',;:()' and not prot[i]:
        prev = t[i - 1] if i else ''
        nxt = t[i + 1] if i + 1 < n else ''
        if not (cjk(prev) or cjk(nxt)):
            rows.append((i, c, prev, nxt, t[max(0, i - 30):i + 30].replace('\n', ' ')))

print('=== NOT adjacent to CJK: %d' % len(rows))
for i, c, p, q, ctx in rows:
    print('%-5d %r prev=%r next=%r | %s' % (i, c, p, q, ctx))
