from pathlib import Path
import hashlib
import json
import fitz

root = Path(__file__).resolve().parents[1]
snapshot = json.loads((root / 'scratch/visual-source-hashes.json').read_text(encoding='utf-8'))
changed = [p for p,h in snapshot.items() if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h]
assert not changed, changed
print(f'Canonical evidence unchanged: {len(snapshot)} files')
out = root / 'scratch/visual_review/framework_semantic'
out.mkdir(parents=True, exist_ok=True)
doc = fitz.open(root / 'paper/main.pdf')
titles = ['四个子问题的总体框架', '数据处理', '质量合成与配比', '广义标度律的参数估计与跨源检验流程', '算力约束', '能力变化分解与前沿情景预测流程']
pages = []
for i,p in enumerate(doc):
    text = p.get_text()
    # Figure titles from actual .lof, plus direct labels present in the rendered diagrams.
    if any(t in text for t in ['跨源检验流程','情景预测流程','KKT','可追溯的数据输入','共同检验','门控质量合成']):
        p.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(out / f'page-{i+1}.png')
        pages.append(i+1)
print('PDF pages:',len(doc),'framework render pages:',pages)
log=(root/'paper/main.log').read_text(encoding='utf-8',errors='replace')
bad=[s for s in log.splitlines() if any(t in s for t in ['Overfull','Missing character','undefined references','undefined citations'])]
assert not bad,bad
print('No overflow, missing glyph, undefined citation/reference warnings')
