"""Create the four per-subquestion state manifests after problem parsing."""
import json
from pathlib import Path

NOW = '2026-09-23T23:58:00+08:00'
OUT = Path('planning/manifests')

TITLES = {
    'Q1': '数据质量评价、质量冲突消解与领域配比建模',
    'Q2': '跨维度数据融合与广义标度律',
    'Q3': '算力约束下的多维资源联合优化与结构性转移',
    'Q4': '技术演进分析与前沿预测',
}
DEPS = {'Q1': [], 'Q2': ['Q1'], 'Q3': ['Q1', 'Q2'], 'Q4': ['Q2']}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for qid, title in TITLES.items():
        m = {
            'schema_version': 1,
            'question_id': qid,
            'title': title,
            'rigor_profile': 'lean',
            'current_gate': 'G1',
            'status': 'parsed_waiting_classification',
            'depends_on': DEPS[qid],
            'artifacts': {
                'parse': 'planning/parse/problem_parse.json',
                'classification': None,
                'data_profile': None,
                'method_card': None,
                'decision_ledger': None,
                'risk_probe': None,
                'latest_run': None,
            },
            'allowed': {
                'code_generation': False,
                'freeze': False,
                'paper_writing': False,
                'final_assembly': False,
            },
            'blockers': [
                f'G1 未通过：{qid} 的成功标准需使用者确认（HD-2）',
                'G1 未通过：题型分类未完成',
            ],
            'next_action': {
                'owner': 'ai',
                'skill': 'problem-classifier',
                'reason': '解析已完成，需先分类再做数据画像',
            },
            'updated_at': NOW,
        }
        p = OUT / f'{qid}.json'
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        print('wrote', p)


if __name__ == '__main__':
    main()
