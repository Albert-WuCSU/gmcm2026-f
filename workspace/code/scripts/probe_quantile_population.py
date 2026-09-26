"""Quantify how much the quantile-normalisation population matters.

A1 covers 7 domains; A2 is arxiv-only (17523 rows); A3 is github-only (203752).
Pooling all three puts 74.9% of the mass on github, so a pooled p05/p95 is
largely a github quantile. This script measures the resulting distortion so the
choice of population is made on evidence, not convenience.
"""
import json
import lzma
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value')
SOURCES = {
    'A1': (ROOT / 'slimpajama_quality_signal_sample.jsonl.xz', None),
    'A2': (ROOT / 'slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz',
           'arxiv'),
    'A3': (ROOT / 'slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz',
           'github'),
}

# Scalar indicators only; list fields need scalarising first (separate decision).
PROBE = ['fineweb_edu_s', 'qurater_s', 'rps_doc_unigram_entropy',
         'rps_doc_frac_unique_words', 'rps_doc_mean_word_length',
         'rps_doc_word_count']


def scalarise(o):
    """Minimal, evidence-based scalars for the probe (see probe_list_semantics)."""
    out = {}
    fw = o.get('fineweb_edu')
    out['fineweb_edu_s'] = fw[0] if isinstance(fw, list) and fw else None
    q = o.get('qurater')
    if isinstance(q, list) and q and all(
            isinstance(x, (int, float)) and math.isfinite(x) for x in q):
        out['qurater_s'] = sum(q) / len(q)
    else:
        out['qurater_s'] = None
    for k in ('rps_doc_unigram_entropy', 'rps_doc_frac_unique_words',
              'rps_doc_mean_word_length', 'rps_doc_word_count'):
        v = o.get(k)
        out[k] = v if isinstance(v, (int, float)) and math.isfinite(v) else None
    return out


def quantiles(vals, ps=(0.05, 0.50, 0.95)):
    s = sorted(vals)
    if not s:
        return {}
    return {f'p{int(p*100):02d}': s[min(int(p * (len(s) - 1)), len(s) - 1)]
            for p in ps}


def main():
    by_domain = defaultdict(lambda: defaultdict(list))
    by_file = defaultdict(lambda: defaultdict(list))
    pooled = defaultdict(list)

    for tag, (path, forced_domain) in SOURCES.items():
        with lzma.open(path, 'rt', encoding='utf-8') as fh:
            for line in fh:
                o = json.loads(line)
                dom = forced_domain or o.get('_source_domain') or 'unknown'
                sc = scalarise(o)
                for k, v in sc.items():
                    if v is None:
                        continue
                    by_domain[dom][k].append(v)
                    by_file[tag][k].append(v)
                    pooled[k].append(v)

    print('=== row mass by domain (pooled A1+A2+A3) ===')
    tot = sum(len(by_domain[d]['fineweb_edu_s']) for d in by_domain)
    for d in sorted(by_domain, key=lambda x: -len(by_domain[x]['fineweb_edu_s'])):
        n = len(by_domain[d]['fineweb_edu_s'])
        print(f'  {d:16s} {n:7d}  {100*n/tot:6.2f}%')

    report = {'domain_mass': {d: len(by_domain[d]['fineweb_edu_s'])
                              for d in by_domain},
              'pooled_total': tot, 'per_field': {}}

    print()
    print('=== p05/p95 under three candidate populations ===')
    for k in PROBE:
        qp = quantiles(pooled[k])
        entry = {'pooled': qp, 'by_file': {}, 'by_domain': {}}
        print(f'\n{k}')
        print(f'  pooled          p05={qp["p05"]:>12.4f} p50={qp["p50"]:>12.4f} '
              f'p95={qp["p95"]:>12.4f}  n={len(pooled[k])}')
        for tag in ('A1', 'A2', 'A3'):
            if not by_file[tag][k]:
                continue
            q2 = quantiles(by_file[tag][k])
            entry['by_file'][tag] = q2
            print(f'  {tag:15s} p05={q2["p05"]:>12.4f} p50={q2["p50"]:>12.4f} '
                  f'p95={q2["p95"]:>12.4f}  n={len(by_file[tag][k])}')
        for d in sorted(by_domain):
            if len(by_domain[d][k]) < 50:
                continue
            q3 = quantiles(by_domain[d][k])
            entry['by_domain'][d] = q3
        # distortion: pooled range vs A1 range
        a1 = entry['by_file'].get('A1')
        if a1:
            pr = qp['p95'] - qp['p05']
            ar = a1['p95'] - a1['p05']
            ratio = pr / ar if ar else None
            entry['pooled_over_A1_range_ratio'] = ratio
            print(f'  -> pooled(p95-p05)/A1(p95-p05) = {ratio:.3f}')
        report['per_field'][k] = entry

    Path('workspace/data/quantile_population.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print('\nwrote workspace/data/quantile_population.json')


if __name__ == '__main__':
    main()
