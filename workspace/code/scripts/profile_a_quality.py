"""Profile the SlimPajama quality signals (A1/A2/A3) by streaming.

Goals that later gates depend on:
  * establish what the 8 list-type indicators actually contain, so scalarisation
    is an evidence-based choice rather than a guess;
  * quantify missingness and distribution shape per indicator;
  * settle the quantile-population question (A3 is 11.6x A2, so a pooled
    quantile is dominated by github).

Streams with lzma so the 165MB/103MB files never land in memory at once.
Raw files are read-only and never rewritten.
"""
import json
import lzma
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value')
OUT = Path('workspace/data')
SEED = 20260924
SAMPLE_CAP = 20000  # reservoir size per (file, field, position) for quantiles

SOURCES = {
    'A1': ROOT / 'slimpajama_quality_signal_sample.jsonl.xz',
    'A2': ROOT / 'slimpajama_quality_extended/arxiv_part-6777d8857c6e-000486.jsonl.xz',
    'A3': ROOT / 'slimpajama_quality_extended/github_part-6777d8857c6e-000275.jsonl.xz',
}

AUX_FIELDS = {'id', 'content', 'sub_path', '_source_domain', '_source_path'}


class Stream:
    """Running stats plus a fixed-size reservoir for quantiles."""

    def __init__(self, seed):
        self.n = 0
        self.n_null = 0
        self.total = 0.0
        self.sq = 0.0
        self.lo = math.inf
        self.hi = -math.inf
        self.res = []
        self.rng = random.Random(seed)

    def add(self, v):
        if v is None:
            self.n_null += 1
            return
        try:
            v = float(v)
        except (TypeError, ValueError):
            self.n_null += 1
            return
        if not math.isfinite(v):
            self.n_null += 1
            return
        self.n += 1
        self.total += v
        self.sq += v * v
        self.lo = min(self.lo, v)
        self.hi = max(self.hi, v)
        if len(self.res) < SAMPLE_CAP:
            self.res.append(v)
        else:
            j = self.rng.randrange(self.n)
            if j < SAMPLE_CAP:
                self.res[j] = v

    def summary(self):
        if self.n == 0:
            return {'n': 0, 'n_null': self.n_null, 'note': 'no finite values'}
        mean = self.total / self.n
        var = max(self.sq / self.n - mean * mean, 0.0)
        s = sorted(self.res)

        def q(p):
            if not s:
                return None
            k = min(int(p * (len(s) - 1)), len(s) - 1)
            return s[k]

        return {
            'n': self.n, 'n_null': self.n_null,
            'mean': mean, 'std': math.sqrt(var),
            'min': self.lo, 'max': self.hi,
            'p01': q(0.01), 'p05': q(0.05), 'p25': q(0.25), 'p50': q(0.50),
            'p75': q(0.75), 'p95': q(0.95), 'p99': q(0.99),
            'sample_size_for_quantiles': len(s),
        }


def profile_file(tag, path):
    scalar = defaultdict(lambda: Stream(SEED))
    listpos = defaultdict(lambda: Stream(SEED))     # (field, idx) -> stats
    list_len = defaultdict(Counter)                  # field -> Counter(len)
    list_argmax = defaultdict(Counter)               # field -> Counter(argmax idx)
    field_seen = Counter()
    domains = Counter()
    n_rows = 0
    field_sets = Counter()

    with lzma.open(path, 'rt', encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            n_rows += 1
            field_sets[tuple(sorted(obj))] += 1
            if '_source_domain' in obj:
                domains[obj['_source_domain']] += 1
            for k, v in obj.items():
                field_seen[k] += 1
                if k in AUX_FIELDS:
                    continue
                if isinstance(v, list):
                    list_len[k][len(v)] += 1
                    vals = []
                    for i, x in enumerate(v):
                        listpos[(k, i)].add(x)
                        try:
                            vals.append(float(x))
                        except (TypeError, ValueError):
                            vals.append(-math.inf)
                    if vals:
                        list_argmax[k][max(range(len(vals)), key=lambda i: vals[i])] += 1
                else:
                    scalar[k].add(v)

    return {
        'tag': tag,
        'path': str(path).replace('\\', '/'),
        'rows': n_rows,
        'distinct_field_sets': len(field_sets),
        'fields_present': dict(field_seen),
        'domains': dict(domains) or None,
        'scalar_fields': {k: v.summary() for k, v in sorted(scalar.items())},
        'list_fields': {
            k: {
                'length_counts': dict(sorted(list_len[k].items())),
                'argmax_counts': dict(sorted(list_argmax[k].items())),
                'per_position': {
                    str(i): listpos[(k, i)].summary()
                    for i in range(max(list_len[k]))
                },
            }
            for k in sorted(list_len)
        },
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for tag, path in SOURCES.items():
        print(f'profiling {tag} ...', flush=True)
        report[tag] = profile_file(tag, path)
        r = report[tag]
        print(f'  rows={r["rows"]} scalar={len(r["scalar_fields"])} '
              f'list={len(r["list_fields"])} field_sets={r["distinct_field_sets"]}',
              flush=True)

    p = OUT / 'profile_a_quality.json'
    p.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print('wrote', p)


if __name__ == '__main__':
    main()
