import io, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

a = io.open('scratch/problem1.tex.bak', encoding='utf-8').read()
b = io.open('paper/sections/problem1.tex', encoding='utf-8').read()

LAB = re.compile(r'\\label\{([^}]*)\}')
REF = re.compile(r'\\(?:ref|eqref)\{([^}]*)\}')
CIT = re.compile(r'\\cite[pt]?\{([^}]*)\}')


def parts(t):
    return (sorted(LAB.findall(t)), sorted(REF.findall(t)), CIT.findall(t))


la, ra, ca = parts(a)
lb, rb, cb = parts(b)
print('labels    %d -> %d  same set: %s' % (len(la), len(lb), la == lb))
print('refs      %d -> %d  same set: %s' % (len(ra), len(rb), ra == rb))
print('citations %d -> %d  same sequence: %s' % (len(ca), len(cb), ca == cb))

bad = [x for x in re.findall(r'\\(?:label|ref|eqref|cite[pt]?)\{[^}]*\}', b)
       if any(ord(c) > 127 for c in x)]
print('non-ASCII inside label/ref/cite keys:', bad)

MATH = re.compile(r'(?<!\\)\$[^$]*\$')


def mathsegs(t):
    out = [m.group() for m in MATH.finditer(t)]
    for m in re.finditer(r'\\begin\{equation\}.*?\\end\{equation\}', t, re.S):
        out.append(m.group())
    return out


ma, mb = mathsegs(a), mathsegs(b)
print('math segments %d -> %d  identical: %s' % (len(ma), len(mb), ma == mb))
if ma != mb:
    for x, y in zip(ma, mb):
        if x != y:
            print('  DIFF', repr(x)[:100], '||', repr(y)[:100])

TAB = re.compile(r'\\begin\{tabular\}.*?\\end\{tabular\}', re.S)
ta = [re.sub(r'\s+', ' ', m.group()) for m in TAB.finditer(a)]
tb = [re.sub(r'\s+', ' ', m.group()) for m in TAB.finditer(b)]
print('tabular blocks %d -> %d' % (len(ta), len(tb)))
for i, (x, y) in enumerate(zip(ta, tb)):
    if x != y:
        print('  --- block %d differs:' % i)
        print('   before:', x)
        print('   after :', y)

# numeric intervals must be untouched
for pat in [r'\(0\.\d+, 0\.\d+\)', r'\d\\,\d{3}']:
    print(pat, 'before', len(re.findall(pat, a)), 'after', len(re.findall(pat, b)))
