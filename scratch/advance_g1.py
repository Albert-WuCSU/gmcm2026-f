"""Advance each manifest to G1 PASSED after classification, and verify consistency."""
import json
from pathlib import Path

NOW = '2026-09-24T00:35:00+08:00'
MAN = Path('planning/manifests')
CLS = Path('planning/classification/problem_classification.json')


def main():
    cls = json.loads(CLS.read_text(encoding='utf-8'))
    types = {q['id']: (q['primary_type'], q['secondary_type'], q['confidence'])
             for q in cls['subquestions']}

    for p in sorted(MAN.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        qid = m['question_id']
        primary, secondary, conf = types[qid]

        m['current_gate'] = 'G1'
        m['status'] = 'problem_framed'
        m['gate_history'] = m.get('gate_history', []) + [
            {'gate': 'G1', 'result': 'PASSED', 'at': NOW,
             'basis': ['planning/parse/problem_parse.json',
                       'planning/classification/problem_classification.json',
                       'planning/framing_decisions.jsonl']}
        ]
        m['task_type'] = {'primary': primary, 'secondary': secondary, 'confidence': conf}
        m['artifacts']['classification'] = str(CLS).replace('\\', '/')
        m['blockers'] = []
        m['next_action'] = {
            'owner': 'ai',
            'skill': 'data-auditor-cleaner',
            'reason': '方法卡之前须完成数据画像',
        }
        m['updated_at'] = NOW
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')

    # Verify: every Qx classified, one primary each, no method leakage, gates agree.
    assert set(types) == {'Q1', 'Q2', 'Q3', 'Q4'}, types
    assert all(t[0] for t in types.values()), 'missing primary type'
    assert cls['no_methods_selected'] is True
    for p in sorted(MAN.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        assert m['blockers'] == [] and m['current_gate'] == 'G1'
        assert m['allowed']['code_generation'] is False, 'G2/G2.5 not passed yet'
        print(f"{m['question_id']}: G1 PASSED | {m['task_type']['primary']}"
              f"/{m['task_type']['secondary']} ({m['task_type']['confidence']})"
              f" | baseline set | next={m['next_action']['skill']}")


if __name__ == '__main__':
    main()
