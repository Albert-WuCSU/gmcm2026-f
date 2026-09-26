"""Update manifests after the data audit and verify raw data is still untouched."""
import json
import os
from pathlib import Path

NOW = '2026-09-24T14:30:00+08:00'
MAN = Path('planning/manifests')

READINESS = {
    'Q1': ('ready_with_warnings', ['F2 域混淆：Q 有退化为域标签的风险，分位数须按域计算',
                                   'F4 A16 仅 6/17 域有质量域对应',
                                   'F5 配方稀疏，ILR 已排除',
                                   'F3 book 域仅 171 条']),
    'Q2': ('ready_with_warnings', ['F8 Q 尺度对齐为首要风险：经验 Q 与设计网格 Q 非同类对象',
                                   'B6-B8 半合成且为唯一含 Q 数据',
                                   'D_eff 形式的 beta/gamma 乘积退化（见思路评审 3.2）']),
    'Q3': ('ready', ['依赖 Q1/Q2 输出；C7 可行 L_ctx 已确认 5 个取值，2 个跨越临界值 30000']),
    'Q4': ('ready_with_warnings', ['F11 密集窗口 15 个月 < 预测窗口 24 个月',
                                   'F9 桥接高可比仅 7 条',
                                   'F12 pretrained 仅 275 条 (6.0%)',
                                   'C3 历史锚点仅 24 行']),
}


def main():
    for p in sorted(MAN.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        qid = m['question_id']
        status, warns = READINESS[qid]
        m['artifacts']['data_profile'] = 'workspace/data/data_profile.json'
        m['artifacts']['data_report'] = 'workspace/data/data_report.md'
        m['data_readiness'] = {'status': status, 'warnings': warns}
        m['status'] = 'data_profiled_ready_for_method_screening'
        m['next_action'] = {'owner': 'ai', 'skill': 'method-selector',
                            'reason': '数据画像完成，可进入 G2 方法筛选与风险探针'}
        m['updated_at'] = NOW
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{qid}: {status} ({len(warns)} warnings)')

    # raw data must still be read-only and unchanged in count
    raw = [p for p in Path('workspace/data_raw').rglob('*') if p.is_file()]
    writable = [p for p in raw if os.access(p, os.W_OK)]
    print(f'\nraw files: {len(raw)}  writable: {len(writable)}')
    assert len(raw) == 2014, f'raw file count changed: {len(raw)}'
    assert not writable, f'{len(writable)} raw files became writable'
    print('raw data intact: 2014 files, all read-only')

    for p in sorted(MAN.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        assert m['current_gate'] == 'G1' and m['allowed']['code_generation'] is False
    print('gates: all G1, code_generation still False (G2/G2.5 not yet passed)')


if __name__ == '__main__':
    main()
