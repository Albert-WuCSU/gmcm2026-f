"""D1/D2 wording fixes from the consistency audit."""
import pathlib

SEC = pathlib.Path('paper/sections')

FIXES = [
    ('assumptions.tex',
     '$C$ & 算力预算 & FLOPs & 问题三按 $10^{21}$ FLOPs 标度给出，'
     '正文以 $10^{19}$、$10^{22}$、$10^{24}$ 锚定 ' + chr(92) * 2,
     '$C$ & 算力预算 & FLOPs & 问题三沿 $10^{18}$--$10^{25}$ 扫描，'
     '以 $10^{19}$、$10^{22}$、$10^{24}$ 三档锚定 ' + chr(92) * 2,
     'D2 remove the stray 1e21 scale claim'),
    ('problem1.tex',
     '下方为本节交付物：领域序及其最高一档、供问题二使用的领域级 $Q$、'
     '配比到损失的拟合优度，',
     '下方为本节交付物：领域序及其最高一档、领域级 $Q$（供问题二对照，'
     '其刻度对齐见问题二）、配比到损失的拟合优度，',
     'D1 the domain Q is for cross-checking, not direct substitution'),
]

for name, old, new, note in FIXES:
    p = SEC / name
    t = p.read_text(encoding='utf-8')
    ok = old in t
    print(('OK   ' if ok else 'MISS ') + name + ': ' + note)
    if not ok:
        print('       looked for:', repr(old[:80]))
    else:
        p.write_text(t.replace(old, new), encoding='utf-8')
