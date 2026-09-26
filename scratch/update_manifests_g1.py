"""Record the HD-2/HD-3 framing decisions in each subquestion manifest.

G1 still needs classification, so the gate does not advance here; only the
framing blocker clears and each question gains its declared baseline.
"""
import json
from pathlib import Path

NOW = '2026-09-24T00:22:00+08:00'
OUT = Path('planning/manifests')

BASELINES = {
    'Q1': '等权平均（Q1a）/ 无消解等权（Q1b）/ 带单纯形约束的线性回归（Q1c）',
    'Q2': '经典标度律 L=E+A·N^-alpha+B·D^-beta（不含 Q、p）',
    'Q3': 'Chinchilla 经验配置（N 与 D 成比例，忽略 Q 与 attn 开销）',
    'Q4': '纯时间趋势外推（不分解规模/技术进步）',
}


def main():
    for p in sorted(OUT.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        qid = m['question_id']

        m['success_criteria_mode'] = 'relative_to_baseline'
        m['declared_baseline'] = BASELINES[qid]
        m['scope_profile'] = 'mandatory_plus_A18_sampling'
        m['artifacts']['framing_decisions'] = 'planning/framing_decisions.jsonl'
        m['artifacts']['choice_card'] = 'planning/choice_cards/hd2_hd3_framing_card.md'

        # HD-2 settles the success-criteria blocker; classification still pending.
        m['blockers'] = ['G1 未通过：题型分类未完成']
        m['status'] = 'framing_decided_waiting_classification'
        m['updated_at'] = NOW

        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"{qid}: baseline={BASELINES[qid][:40]}... blockers={len(m['blockers'])}")


if __name__ == '__main__':
    main()
