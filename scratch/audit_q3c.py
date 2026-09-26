import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
s = open('paper/sections/problem3.tex', encoding='utf-8').read()
lines = s.split('\n')
pat = re.compile(r'\d+(?:\.\d+)?(?:\\times10\^\{[^}]*\})?')
for i, l in enumerate(lines, 1):
    found = pat.findall(l)
    found = [f for f in found if f not in ('0', '1', '2', '3', '4', '5', '6', '7', '10', '17', '18', '19', '22', '24', '25', '57', '2048')]
    if found:
        print(i, found)
