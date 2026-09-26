"""A18 sampling: independent text statistics per RegMix domain (HD-3=B commitment).

Purpose is NOT to reproduce the 22 quality indicators (those are model scores we
cannot recompute) but to obtain self-computed, transparent text statistics that
can be compared *in trend* against the quality side, so the A16 cross-system
mapping gets one independent check.

Declared limitation, to be carried into the paper: these statistics are computed
by us; the 22 indicators in A1-A3 are dataset-provided model outputs. Only
trend/rank agreement is meaningful; absolute values are not comparable.

Reservoir-samples per domain in a single streaming pass with a fixed seed.
"""
import json
import lzma
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path('workspace/data_raw/real_attachments/A_data_value/regmix_domain_sample.jsonl.xz')
OUT_JSON = Path('workspace/data/a18_text_stats.json')
OUT_CLEAN = Path('workspace/data_clean/a18_domain_text_stats.csv')
SEED = 20260924
PER_DOMAIN = 300          # reservoir size per domain
WORD = re.compile(r"[A-Za-z']+")


def text_features(t):
    """Transparent, recomputable statistics only."""
    n_chars = len(t)
    if n_chars == 0:
        return None
    words = WORD.findall(t)
    n_words = len(words)
    lines = t.split('\n')
    n_lines = len(lines)
    sents = [s for s in re.split(r'[.!?]+', t) if s.strip()]
    alpha = sum(ch.isalpha() for ch in t)
    digit = sum(ch.isdigit() for ch in t)
    upper = sum(ch.isupper() for ch in t)
    space = sum(ch.isspace() for ch in t)
    uniq = len(set(w.lower() for w in words))

    # unigram entropy over lowercased words
    ent = 0.0
    if n_words:
        c = Counter(w.lower() for w in words)
        for k in c.values():
            p = k / n_words
            ent -= p * math.log(p)

    return {
        'n_chars': n_chars,
        'n_words': n_words,
        'n_lines': n_lines,
        'n_sentences': len(sents),
        'mean_word_length': (sum(len(w) for w in words) / n_words) if n_words else 0.0,
        'frac_unique_words': (uniq / n_words * 100) if n_words else 0.0,
        'unigram_entropy': ent,
        'frac_alpha': alpha / n_chars * 100,
        'frac_digit': digit / n_chars * 100,
        'frac_upper': upper / n_chars * 100,
        'frac_space': space / n_chars * 100,
        'mean_line_length': n_chars / n_lines if n_lines else 0.0,
    }


def summarize(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    mean = sum(s) / n
    return {'n': n, 'mean': mean, 'p25': s[n // 4], 'p50': s[n // 2],
            'p75': s[3 * n // 4]}


def main():
    rng = random.Random(SEED)
    res = defaultdict(list)     # domain -> reservoir of texts
    seen = Counter()

    with lzma.open(SRC, 'rt', encoding='utf-8') as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            dom = (o.get('_source_domain') or 'unknown').strip()
            t = o.get('text') or ''
            if not t:
                continue
            seen[dom] += 1
            r = res[dom]
            if len(r) < PER_DOMAIN:
                r.append(t)
            else:
                j = rng.randrange(seen[dom])
                if j < PER_DOMAIN:
                    r[j] = t

    print(f'domains seen: {len(seen)}  total records: {sum(seen.values())}')
    for d in sorted(seen, key=lambda x: -seen[x]):
        print(f'  {d:24s} total={seen[d]:7d} sampled={len(res[d])}')

    feats = ['n_chars', 'n_words', 'n_lines', 'n_sentences', 'mean_word_length',
             'frac_unique_words', 'unigram_entropy', 'frac_alpha', 'frac_digit',
             'frac_upper', 'frac_space', 'mean_line_length']
    per_domain = {}
    for d, texts in res.items():
        rows = [f for t in texts if (f := text_features(t))]
        per_domain[d] = {k: summarize([r[k] for r in rows]) for k in feats}
        per_domain[d]['_n_sampled'] = len(rows)
        per_domain[d]['_n_total'] = seen[d]

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(
        {'seed': SEED, 'per_domain_cap': PER_DOMAIN,
         'limitation': 'self-computed statistics; NOT comparable in absolute value '
                       'to the dataset-provided 22 quality indicators; trend/rank only',
         'domain_totals': dict(seen), 'per_domain': per_domain},
        ensure_ascii=False, indent=1), encoding='utf-8')

    OUT_CLEAN.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CLEAN.open('w', encoding='utf-8', newline='') as fh:
        fh.write('domain,n_total,n_sampled,' + ','.join(f'{k}_p50' for k in feats) + '\n')
        for d in sorted(per_domain):
            v = per_domain[d]
            cells = [f'{v[k]["p50"]:.4f}' if v[k] else '' for k in feats]
            fh.write(f'{d},{v["_n_total"]},{v["_n_sampled"]},' + ','.join(cells) + '\n')

    print(f'\nwrote {OUT_JSON}')
    print(f'wrote {OUT_CLEAN}')
    print('\n=== median text stats by domain ===')
    print(f'{"domain":24s} {"n_words":>9s} {"entropy":>8s} {"uniq%":>7s} {"digit%":>7s} {"wordlen":>8s}')
    for d in sorted(per_domain, key=lambda x: -(per_domain[x]['n_words']['p50'] or 0)):
        v = per_domain[d]
        print(f'{d:24s} {v["n_words"]["p50"]:9.0f} {v["unigram_entropy"]["p50"]:8.3f} '
              f'{v["frac_unique_words"]["p50"]:7.2f} {v["frac_digit"]["p50"]:7.2f} '
              f'{v["mean_word_length"]["p50"]:8.3f}')


if __name__ == '__main__':
    main()
