"""Fold the idea-document review into the manifests as carried-forward todos."""
import json
from pathlib import Path

NOW = '2026-09-24T11:30:00+08:00'
MAN = Path('planning/manifests')
REVIEW = 'planning/review_of_user_ideas.md'

# Changes that must survive into later gates, per question.
CARRIED = {
    'Q1': [
        '分位数标准化的总体口径须定义（合并全体 / 按域 / 以 A1 为参照）；A3 占合并样本 74.9%，会主导全局分位数',
        '域级聚合改用 Huber/截尾均值 + bootstrap 区间，以应对 A2:A3 = 1:11.6 的样本量不平衡',
        'ILR 变换不采纳：512 行中 511 行含精确零、每行中位约 8/17 个域为零，伪计数会主导坐标；须在方法卡记录为“考察过但排除”',
        '4 个无 Loss 列域（enron_emails/philpapers/nih_exporter/europarl）恰为最常为零的域，须纳入处理方式论证',
        '冲突定义候选：全局加权 MAD/方差 + 局部“高价值×高污染”相反高分对；消解用 Q=V-P 或门控乘积',
    ],
    'Q2': [
        'D_eff = D·Q^gamma·exp(b^T z_p) 形式隐含 Q-vs-D 弹性比恒等于 gamma（已数值验证，8 个测点均为 2.0000）',
        '沿 Q 方向仅可辨识乘积 beta*gamma：须先由 B1 真实 N-D 数据钉住 beta，再用 B6-B8 估计 gamma',
        '论文不得同时声称“Q 与 D 替代率随位置变化”与采用该形式，二者矛盾（仅 Q-vs-N 随位置变化）',
        '等价条件 dL=0 解 ΔN/ΔQ，须对后验/重抽样样本逐一计算并输出区间，不报单一常数',
    ],
    'Q3': [
        '实验设计改为 log C 轴密集扫描，三档预算（1e19/1e22/1e24）作为报告锚点而非全部计算点——三点无法定位转移位置',
        '结构性转移主定义：KKT 活跃约束集改变，或预算份额向量 L1 距离 > delta 且在邻域持续',
        '写作红线：L_ctx^crit = 30000 仅为两类成本相等的临界尺度，不得表述为“最优上下文长度”',
        '从 Scaling Law 后验/重抽样抽参重复优化，输出最优配置置信带而非点解',
        '变量须限制在数据支持或合理外推范围内，否则优化器会跑到无数据支持的极端区',
    ],
    'Q4': [
        '缺失 benchmark 用可比样本子集或层次模型，不得填 0',
        '贡献表述为“非规模技术/数据工程综合进步”，不过度因果化（时间项会吸收未观测的数据质量变化）',
        '桥接须对 pretrained / chat 分别检验是否需要不同映射；映射误差作为独立随机项传播到前沿预测',
        '前沿用 0.9/0.95 分位数定义；报告中位数与 80%/95% 区间，不给虚假精确点值',
        'Monte Carlo 同时抽取标度律参数、桥接误差与技术趋势三个不确定性来源',
    ],
}

GLOBAL = [
    '每个数据编号增加 confidence_tier 与 fit_allowed 字段；禁止把半合成与真实观测等权拟合',
    '实验设计四件套：baseline + 主方法 + 消融 + 参数扰动',
    '不可行候选须记录违反了哪条约束及违反程度，而非只给极大惩罚值',
]


def main():
    for p in sorted(MAN.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        qid = m['question_id']
        m['carried_forward_todos'] = CARRIED[qid] + GLOBAL
        m['artifacts']['idea_review'] = REVIEW
        m['updated_at'] = NOW
        p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'{qid}: {len(CARRIED[qid])} question-specific + {len(GLOBAL)} global todos')

    # Gates must not have moved.
    for p in sorted(MAN.glob('Q*.json')):
        m = json.loads(p.read_text(encoding='utf-8'))
        assert m['current_gate'] == 'G1' and m['blockers'] == []
        assert m['allowed']['code_generation'] is False
    print('gates unchanged: all G1, no blockers, code_generation still False')


if __name__ == '__main__':
    main()
