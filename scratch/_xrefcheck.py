import re, glob, os, collections
D = r'D:/Users/luqianwu/Desktop/华为杯/paper'
files = sorted(glob.glob(D + '/sections/*.tex')) + [D + '/main.tex', D + '/anonymous.tex']
labels = collections.defaultdict(list)
refs = collections.defaultdict(list)
figs = collections.defaultdict(list)
LAB = re.compile(r'\\label\{([^}]*)\}')
REF = re.compile(r'\\(?:ref|eqref|autoref)\{([^}]*)\}')
FIG = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}')
for f in files:
    t = open(f, encoding='utf-8').read()
    n = os.path.basename(f)
    for m in LAB.findall(t): labels[m].append(n)
    for m in REF.findall(t): refs[m].append(n)
    for m in FIG.findall(t): figs[os.path.basename(m)].append(n)

print("DUPLICATE LABELS:", {k: v for k, v in labels.items() if len(v) > 1} or "none")
print()
print("REFS TO MISSING LABELS:", {k: sorted(set(v)) for k, v in refs.items() if k not in labels} or "none")
print()
print("FIGURE USAGE:")
for k in sorted(figs):
    secs = sorted(set(figs[k]))
    flag = "  <== MULTI-SECTION" if len(secs) > 1 else ""
    print("  ", k, "<-", secs, flag)
print()
print("LABELS DEFINED BUT NEVER REFERENCED:")
for k, v in sorted(labels.items()):
    if k not in refs:
        print("  ", k, "in", v)
