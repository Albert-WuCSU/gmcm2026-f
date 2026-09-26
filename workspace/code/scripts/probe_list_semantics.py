"""Decide how to scalarise the 8 list-type quality indicators, with evidence.

Hypotheses to test on A1:
  H1  ad_en / fluency_en are paired binary logits -> pos0 ~ -pos1, so the mean
      is uninformative and the correct scalar is the logit margin (or sigmoid).
  H2  modernbert_* are 6-class ordinal logits -> the softmax-expected class
      index preserves order; a plain mean of logits does not.
  H3  qurater's 4 entries are separate criteria, not one ordinal scale.

Also measures each candidate scalar against fineweb_edu, whose direction is
known (higher = more educational), to gather directional evidence.
"""
import json
import lzma
import math
from pathlib import Path

SRC = Path('workspace/data_raw/real_attachments/A_data_value/'
           'slimpajama_quality_signal_sample.jsonl.xz')
OUT = Path('workspace/data/list_semantics.json')
LIMIT = 51230

BINARY = ['ad_en', 'fluency_en']
ORDINAL6 = ['modernbert_cleanliness', 'modernbert_readability',
            'modernbert_reasoning', 'modernbert_professionalism']


def softmax(xs):
    m = max(xs)
    e = [math.exp(x - m) for x in xs]
    s = sum(e)
    return [v / s for v in e]


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    return pearson(rank(xs), rank(ys))


def main():
    cols = {}
    rows = 0
    with lzma.open(SRC, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if rows >= LIMIT:
                break
            o = json.loads(line)
            rows += 1
            for f in BINARY:
                v = o[f]
                cols.setdefault(f + '|pos0', []).append(v[0])
                cols.setdefault(f + '|pos1', []).append(v[1])
                cols.setdefault(f + '|mean', []).append(sum(v) / 2)
                cols.setdefault(f + '|margin', []).append(v[1] - v[0])
                cols.setdefault(f + '|sigmoid_p1', []).append(softmax(v)[1])
            for f in ORDINAL6:
                v = o[f]
                p = softmax(v)
                cols.setdefault(f + '|mean', []).append(sum(v) / 6)
                cols.setdefault(f + '|argmax', []).append(
                    float(max(range(6), key=lambda i: v[i])))
                cols.setdefault(f + '|expected_class', []).append(
                    sum(i * pi for i, pi in enumerate(p)))
                cols.setdefault(f + '|top_prob', []).append(max(p))
            q = o['qurater']
            for i, x in enumerate(q):
                cols.setdefault(f'qurater|pos{i}', []).append(x)
            cols.setdefault('qurater|mean', []).append(sum(q) / 4)
            cols.setdefault('fineweb_edu', []).append(o['fineweb_edu'][0])

    out = {'rows': rows, 'tests': {}}

    print(f'rows={rows}')
    print('=== H1: binary logit pairs (corr of pos0 vs pos1) ===')
    h1 = {}
    for f in BINARY:
        r = pearson(cols[f + '|pos0'], cols[f + '|pos1'])
        # how close to exactly antisymmetric?
        sums = [a + b for a, b in zip(cols[f + '|pos0'], cols[f + '|pos1'])]
        sm = sum(sums) / len(sums)
        sv = math.sqrt(sum((x - sm) ** 2 for x in sums) / len(sums))
        h1[f] = {'corr_pos0_pos1': r, 'sum_mean': sm, 'sum_std': sv}
        print(f'  {f:12s} corr={r:+.4f}  (pos0+pos1) mean={sm:+.4f} std={sv:.4f}')
    out['tests']['H1_binary_pairs'] = h1

    print()
    print('=== H2/H3: candidate scalars vs fineweb_edu (known: higher=better) ===')
    fw = cols['fineweb_edu']
    rel = {}
    for name, v in sorted(cols.items()):
        if name == 'fineweb_edu':
            continue
        rel[name] = {'pearson_vs_fineweb_edu': pearson(v, fw),
                     'spearman_vs_fineweb_edu': spearman(v, fw)}
    def fmt(x):
        return f'{x:+.4f}' if x is not None else '  n/a  '

    for name in sorted(rel):
        p = rel[name]['pearson_vs_fineweb_edu']
        s = rel[name]['spearman_vs_fineweb_edu']
        flag = ''
        if p is None or s is None:
            v = cols[name]
            flag = f'  <- CONSTANT? min={min(v)} max={max(v)}'
        print(f'  {name:42s} pearson={fmt(p)} spearman={fmt(s)}{flag}')
    out['tests']['vs_fineweb_edu'] = rel

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print('\nwrote', OUT)


if __name__ == '__main__':
    main()
