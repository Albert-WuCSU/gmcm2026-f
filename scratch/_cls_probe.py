import re

t = open('paper/gmcm2026.cls', encoding='utf-8').read()
pat = re.compile(
    r'\\(?:RequirePackage|usepackage|LoadClass|newenvironment|newcommand'
    r'|renewcommand|DeclareOption|ProcessOptions|definecolor|newtheorem'
    r'|floatstyle|restylefloat|RequirePackageWithOptions)\b[^\n]*'
)
for m in pat.finditer(t):
    print(m.group(0).strip())
print('---- environments ----')
for m in re.finditer(r'\\newenvironment\{([^}]*)\}', t):
    print('env:', m.group(1))
