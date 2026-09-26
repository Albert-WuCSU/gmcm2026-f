"""Test whether a pooled quality score would just be re-encoding the domain.

Evidence from probe_quantile_population.py: for qurater the arxiv p05 sits ABOVE
the github p95, so the two domains barely overlap on that indicator. If several
indicators separate domains that cleanly, a pooled min-max/quantile scaling
produces a "quality" score that mostly answers "which domain is this?" — which
would make the domain-level Q in Q1 circular.

Measures, per indicator, the AUC of a single-feature arxiv-vs-github classifier.
AUC near 1.0 or 0.0 means near-perfect separation by that indicator alone.
"""
import json
import lzma
import math
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value')
A2 = ROOT / 'slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz'
A3 = ROOT / 'slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz'

SCALARS = ['dsir_books', 'dsir_wiki', 'dsir_math', 'rps_doc_word_count',
           'rps_doc_num_sentences', 'rps_doc_unigram_entropy',
           'rps_doc_frac_unique_words', 'rps_doc_frac_no_alph_words',
           'rps_doc_frac_chars_top_2gram', 'rps_doc_frac_chars_top_3gram',
           'rps_lines_uppercase_letter_fraction',
           'rps_lines_ending_with_terminal_punctution_mark',
           'rps_lines_numerical_chars_fraction', 'rps_doc_mean_word_length']


def softmax_expect(v):
    m = max(v)
    e = [math.exp(x - m) for x in v]
    s = sum(e)
    return sum(i * (x / s) for i, x in enumerate(e))


def derived(o):
    """Evidence-based scalars for the 8 list indicators."""
    out = {}
    fw = o.get('fineweb_edu')
    if isinstance(fw, list) and fw and math.isfinite(fw[0]):
        out['fineweb_edu'] = fw[0]
    for f in ('ad_en', 'fluency_en'):
        v = o.get(f)
        if isinstance(v, list) and len(v) == 2 and all(math.isfinite(x) for x in v):
            out[f + '_margin'] = v[1] - v[0]      # paired binary logits
    for f in ('modernbert_cleanliness', 'modernbert_readability',
              'modernbert_reasoning', 'modernbert_professionalism'):
        v = o.get(f)
        if isinstance(v, list) and len(v) == 6 and all(
                isinstance(x, (int, float)) and math.isfinite(x) for x in v):
            out[f + '_expclass'] = softmax_expect(v)   # 6-class ordinal logits
    q = o.get('qurater')
    if isinstance(q, list) and len(q) == 4 and all(math.isfinite(x) for x in q):
        for i, x in enumerate(q):
            out[f'qurater_{i}'] = x
    return out


def auc(pos, neg):
    """Rank-based AUC; 0.5 = no separation, 1.0 or 0.0 = perfect."""
    tagged = [(v, 1) for v in pos] + [(v, 0) for v in neg]
    tagged.sort(key=lambda t: t[0])
    # average ranks for ties
    ranks = [0.0] * len(tagged)
    i = 0
    while i < len(tagged):
        j = i
        while j + 1 < len(tagged) and tagged[j + 1][0] == tagged[i][0]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    sr = sum(r for r, (_, lab) in zip(ranks, tagged) if lab == 1)
    n1, n0 = len(pos), len(neg)
    return (sr - n1 * (n1 + 1) / 2) / (n1 * n0)


def load(path):
    cols = {}
    with lzma.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            o = json.loads(line)
            rec = derived(o)
            for k in SCALARS:
                v = o.get(k)
                if isinstance(v, (int, float)) and math.isfinite(v):
                    rec[k] = v
            for k, v in rec.items():
                cols.setdefault(k, []).append(v)
    return cols


def main():
    print('loading A2 (arxiv) ...', flush=True)
    arx = load(A2)
    print('loading A3 (github) ...', flush=True)
    git = load(A3)

    rows = []
    for k in sorted(set(arx) & set(git)):
        a = auc(arx[k], git[k])
        rows.append((abs(a - 0.5), a, k))
    rows.sort(reverse=True)

    print()
    print('=== single-indicator arxiv-vs-github separation (AUC) ===')
    print(f'{"indicator":46s} {"AUC":>7s}  {"|AUC-.5|":>8s}  verdict')
    out = {}
    for sep, a, k in rows:
        verdict = ('NEAR-PERFECT' if sep > 0.45 else
                   'strong' if sep > 0.35 else
                   'moderate' if sep > 0.20 else 'weak')
        print(f'{k:46s} {a:7.4f}  {sep:8.4f}  {verdict}')
        out[k] = {'auc_arxiv_vs_github': a, 'separation': sep, 'verdict': verdict}

    n_near = sum(1 for s, _, _ in rows if s > 0.45)
    n_strong = sum(1 for s, _, _ in rows if s > 0.35)
    print()
    print(f'indicators with NEAR-PERFECT separation (|AUC-0.5|>0.45): {n_near}/{len(rows)}')
    print(f'indicators with at least strong separation (>0.35):       {n_strong}/{len(rows)}')

    Path('workspace/data/domain_confound.json').write_text(
        json.dumps({'n_arxiv': len(arx['fineweb_edu']),
                    'n_github': len(git['fineweb_edu']),
                    'per_indicator': out,
                    'n_near_perfect': n_near,
                    'n_strong_or_better': n_strong},
                   ensure_ascii=False, indent=1), encoding='utf-8')
    print('wrote workspace/data/domain_confound.json')


if __name__ == '__main__':
    main()
