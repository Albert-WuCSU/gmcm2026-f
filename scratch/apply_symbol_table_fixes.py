"""Final symbol-table and caption alignments."""
import pathlib

SEC = pathlib.Path('paper/sections')
APPLIED, MISSED = [], []


def edit(name, old, new, note):
    p = SEC / name
    t = p.read_text(encoding='utf-8')
    if old in t:
        p.write_text(t.replace(old, new), encoding='utf-8')
        APPLIED.append(f'{name}: {note}')
    else:
        MISSED.append(f'{name}: {note}\n      looked for {old[:90]!r}')


# symbol table: b is the centred theta, not "proportional to w"; drop the duplicate w row
edit('assumptions.tex',
     '$\\boldsymbol{b}$ & 配比项的系数向量 & 无量纲 & '
     '$\\boldsymbol{b}=(b_1,\\dots,b_{17})$，与问题一的系数 $w$ 成比例 ' + '\\\\',
     '$\\boldsymbol{b}$ & 配比项的系数向量 & 无量纲 & '
     '$\\boldsymbol{b}=\\kappa(\\boldsymbol{\\theta}-\\bar\\theta)$，$\\kappa<0$，'
     '在附件 B 上不可辨识 ' + '\\\\',
     'B8 b defined via centred theta and kappa')
edit('assumptions.tex',
     '$w_i$ & 第 $i$ 个领域的损失水平系数 & nats/token & 问题一配比模型的系数 ' + '\\\\' + '\n',
     '',
     'B8 drop the duplicate w row (theta_d is the one used)')
# the figure prints a plain tau, so describe it as such rather than renaming it
edit('assumptions.tex',
     '$\\tau_{\\mathrm{K}}$（问题一） & 域序的 Kendall 秩相关系数 & 无量纲 & '
     '仅用于问题一的域序稳定性；问题四的 $\\tau_t$ 是月度效应，二者不同 ' + '\\\\',
     '$\\tau$（问题一，无下标） & 域序的 Kendall 秩相关系数 & 无量纲 & '
     '仅用于问题一的域序稳定性；问题四的 $\\tau_t$ 是月度效应，二者不同 ' + '\\\\',
     'B6 tau row now matches the figure label')

# D1: the caption sentence wraps across a line, so match the fragment
edit('problem1.tex', '供问题二使用的领域级 $Q$、',
     '领域级 $Q$（供问题二对照，其刻度对齐见问题二）、',
     'D1 domain Q is for cross-checking, not substitution')

print('APPLIED:')
for a in APPLIED:
    print('  ', a)
if MISSED:
    print('MISSED:')
    for m in MISSED:
        print('  ', m)
