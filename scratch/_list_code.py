"""List top-level defs/classes with line spans for the paper appendix selection."""
import ast
import pathlib
import sys

files = [
    'workspace/code/scripts/q1_features.py',
    'code/Q1/q1_common.py',
    'code/Q1/q1_quality_main.py',
    'code/Q1/q1_mixture_baseline.py',
    'code/Q1/q1_mixture_main.py',
    'code/Q2/q2_common.py',
    'code/Q2/q2_scaling_baseline.py',
    'code/Q2/q2_scaling_main.py',
    'code/Q3/q3_common.py',
    'code/Q3/q3_optimize_main.py',
    'code/Q3/q3_optimize_baseline.py',
    'code/Q4/q4_common.py',
    'code/Q4/q4_analysis.py',
    'code/Q4/q4_round2_trend.py',
]

for f in files:
    fp = pathlib.Path(f)
    print('=' * 72)
    print(f, '(exists)' if fp.exists() else '(MISSING)')
    print('=' * 72)
    if not fp.exists():
        continue
    src = fp.read_text(encoding='utf-8', errors='replace')
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        print('  parse error:', exc)
        continue
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = 'class' if isinstance(node, ast.ClassDef) else 'def'
            print(f'  {node.lineno:>5}-{node.end_lineno:<5} {kind} {node.name}')
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    print(f'  {node.lineno:>5}-{node.end_lineno:<5} CONST {t.id}')
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id.isupper():
                print(f'  {node.lineno:>5}-{node.end_lineno:<5} CONST {node.target.id}')
