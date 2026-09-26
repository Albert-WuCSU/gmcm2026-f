"""Consolidate the per-group profiles into data_profile.json.

Adds the confidence_tier / fit_allowed fields committed to in the idea review,
and states per-question readiness. Reads only files produced by the profiling
scripts, so this stays reproducible and does not re-scan the raw data.
"""
import json
from pathlib import Path

DATA = Path('workspace/data')
OUT = DATA / 'data_profile.json'
NOW = '2026-09-24T14:00:00+08:00'

# tier: real | semi_synthetic | extrapolated | subset | interpolated | mixed | reference
# fit_allowed: primary | secondary_weighted | validation_only | not_for_fitting
TIERS = {
    'A1': ('real', 'primary', '质量主样本，51230 条 × 27 字段'),
    'A2': ('real', 'primary', 'arxiv 扩展，17523 条'),
    'A3': ('real', 'primary', 'github 扩展，203752 条'),
    'A4': ('real', 'primary', '训练配比 512×17'),
    'A5': ('real', 'primary', '训练 Loss 512×13'),
    'A6': ('real', 'validation_only', '检验配比 1M'),
    'A7': ('real', 'validation_only', '检验 Loss 1M'),
    'A8': ('real', 'validation_only', '检验配比 60M'),
    'A9': ('real', 'validation_only', '检验 Loss 60M'),
    'A10': ('real', 'validation_only', '检验配比 1B'),
    'A11': ('real', 'validation_only', '检验 Loss 1B'),
    'A12': ('subset', 'not_for_fitting', '10B 配比取自 train 子集，非独立实验'),
    'A13': ('extrapolated', 'not_for_fitting', '10B Loss 由三尺度幂律外推'),
    'A14': ('subset', 'not_for_fitting', '70B 配比取自 train 子集'),
    'A15': ('extrapolated', 'not_for_fitting', '70B Loss 外推'),
    'A16': ('reference', 'not_for_fitting', '人工整理映射表；11/17 目标为空'),
    'A17': ('real', 'secondary_weighted', '域摘要，本版辅助'),
    'A18': ('real', 'secondary_weighted', 'RegMix 原文抽样，HD-3=B 承诺抽样使用'),
    'B1': ('real', 'primary', 'Pythia 真实轨迹，Q2 主拟合'),
    'B2': ('semi_synthetic', 'validation_only', 'Cerebras 校准+噪声；6ND 比值散布仅 0.989-1.024'),
    'B3': ('interpolated', 'validation_only', 'Pythia 检查点插值 8×500'),
    'B4': ('real', 'validation_only', '跨族收敛点 57 行 12 族'),
    'B5': ('real', 'validation_only', '文献标度律 44 行'),
    'B6': ('semi_synthetic', 'secondary_weighted', '唯一含 Q；完全因子 9×5×8=360'),
    'B7': ('semi_synthetic', 'secondary_weighted', '完全因子 9×5×10=450'),
    'B8': ('semi_synthetic', 'secondary_weighted', '15×10×12 缺 96 格；含 extrapolated 720 行'),
    'B9': ('real', 'validation_only', '100B+ 公开报告值 132 行'),
    'B10': ('extrapolated', 'not_for_fitting', '100B+ 预估 Loss，非观测'),
    'B11': ('reference', 'not_for_fitting', '族元数据 18 行'),
    'B12': ('reference', 'not_for_fitting', '检查点索引 1386 行'),
    'C1': ('real', 'primary', '榜单 4576 行；时间跨度仅 9.1 个月'),
    'C2': ('real', 'secondary_weighted', 'C1 + Epoch 匹配列'),
    'C3': ('mixed', 'secondary_weighted', '名义 2019-2025，但 2024 前仅 24 行'),
    'C4': ('real', 'primary', 'Epoch 元数据 3523×57；开源权重列 870 空'),
    'C5': ('mixed', 'secondary_weighted', '桥接 43 行；High 层仅 7 条'),
    'C6': ('mixed', 'primary', '桥接 75 行；High 层仍仅 7 条'),
    'C7': ('real', 'primary', '架构元数据 45 行；L_ctx 唯一依据'),
    'C8': ('real', 'primary', '1863 目录/1958 JSON；1860 可解析，4 截断'),
    'C9': ('real', 'not_for_fitting', '与 C1 六维等价，已选 C1'),
    'C10': ('reference', 'not_for_fitting', '7 目录仅含 README'),
}


def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def main():
    inv = json.loads(Path('scratch/inventory.json').read_text(encoding='utf-8'))['ids']
    aq = load('profile_a_quality.json')
    miss = load('missingness_a.json')
    qpop = load('quantile_population.json')
    conf = load('domain_confound.json')
    amix = load('profile_a_mixture.json')
    bsc = load('profile_b_scaling.json')
    clb = load('profile_c_leaderboard.json')
    c8 = load('profile_c8.json')

    profile = {
        'schema_version': 1,
        'created_at': NOW,
        'raw_root': 'workspace/data_raw/real_attachments/',
        'raw_readonly_verified': True,
        'raw_files': [
            {'id': k, 'path': v['path'], 'bytes': v['bytes'],
             'confidence_tier': TIERS[k][0], 'fit_allowed': TIERS[k][1],
             'note': TIERS[k][2]}
            for k, v in inv.items() if k in TIERS
        ],
        'attachment_mapping': {
            'Q1': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9', 'A10',
                   'A11', 'A12', 'A13', 'A14', 'A15', 'A16', 'A17', 'A18'],
            'Q2': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10',
                   'B11', 'B12', 'Q1_output'],
            'Q3': ['C7', 'appendix_B_cost_functions', 'Q1_output', 'Q2_output'],
            'Q4': ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C8', 'Q2_output'],
        },
        'sub_profiles': {
            'a_quality': 'workspace/data/profile_a_quality.json',
            'a_list_semantics': 'workspace/data/list_semantics.json',
            'a_missingness': 'workspace/data/missingness_a.json',
            'a_quantile_population': 'workspace/data/quantile_population.json',
            'a_domain_confound': 'workspace/data/domain_confound.json',
            'a_mixture': 'workspace/data/profile_a_mixture.json',
            'b_scaling': 'workspace/data/profile_b_scaling.json',
            'c_leaderboard': 'workspace/data/profile_c_leaderboard.json',
            'c8_detailed': 'workspace/data/profile_c8.json',
        },
        'key_findings': {
            'F1_list_field_semantics': {
                'finding': '8 个列表型指标是分类器 logits，非分数',
                'evidence': 'ad_en/fluency_en 两位相关 -0.985/-0.980（成对二分类）；'
                            'modernbert_* 为 6 类有序 logits，softmax 期望类别对 '
                            'fineweb_edu 相关 +0.30~+0.33，而取均值为 -0.09~-0.24（符号相反）',
                'consequence': '标量化必须用 logit 差（二分类）与 softmax 期望类别（有序），'
                               '取均值会自我抵消',
                'source': 'workspace/data/list_semantics.json',
            },
            'F2_domain_confound': {
                'finding': '25 个候选标量中 15 个近乎完美分离 arxiv 与 github',
                'evidence': '|AUC-0.5|>0.45 的有 15 个；最高 modernbert_reasoning '
                            'AUC=0.9957；qurater 的 arxiv p05=2.15 高于 github p95=1.33',
                'consequence': '合并总体归一化会让 Q 退化为域标签；分位数/Min-Max 必须按域计算',
                'source': 'workspace/data/domain_confound.json',
            },
            'F3_domain_mass_imbalance': {
                'finding': 'github 占合并样本 78.44%',
                'evidence': 'github 213752 / arxiv 18942 / c4,stackexchange,wikipedia 各 10000 '
                            '/ commoncrawl 9640 / book 171，总计 272505',
                'consequence': '域级聚合须用稳健均值 + bootstrap；book 域仅 171 条，'
                               '其域级 Q 不确定性远大于其他域',
                'source': 'workspace/data/quantile_population.json',
            },
            'F4_a16_mapping_mostly_empty': {
                'finding': 'A16 中 11/17 个配方域的目标质量域为空',
                'evidence': 'direct 3（arxiv/github/stackexchange）、near_direct 3'
                            '（wikipedia/book/commoncrawl）、inferred 11 全部 (none)',
                'consequence': '即便决定把 Q 引入配比模型，也只有 6/17 维有 Q 可用；'
                               '质量侧 c4 域在配方侧无来源，两体系部分不相交',
                'source': 'workspace/data/profile_a_mixture.json',
            },
            'F5_mixture_zeros': {
                'finding': '配方表极稀疏，ILR 不可直接用',
                'evidence': 'train_1m 512 行中 511 行含精确零，共 3928 个零，'
                            '每行中位约 8/17 个域为零；6 对表 index 全部严格对齐；'
                            '行和偏离 1 最大 0.004',
                'consequence': 'ILR/CLR 的对数比在每行中位 8 个零上不成立，伪计数会主导坐标',
                'source': 'workspace/data/profile_a_mixture.json',
            },
            'F6_zero_vs_noloss_domains': {
                'finding': '4 个无 Loss 列域零值率最高，但非严格对应',
                'evidence': 'enron_emails 68.8%、philpapers 59.8%、nih_exporter 58.0% 居前三，'
                            '但第四名 hackernews 52.5% 有 Loss 列；europarl 51.6% 第五',
                'consequence': '强相关而非等价；处理这 4 列时须同时考虑其低配比属性',
                'source': 'workspace/data/profile_a_mixture.json',
            },
            'F7_unit_consistency_confirmed': {
                'finding': 'C_FLOPs_1e21 与 6ND 的中位比值恰为 1.0000',
                'evidence': 'B1 n=1176 中位 1.0000（范围 0.766-1.763）；'
                            'B2 n=1029 中位 1.0000（范围 0.989-1.024）',
                'consequence': 'C=6ND 口径可用；B2 的极窄散布进一步印证其半合成性质',
                'source': 'workspace/data/profile_b_scaling.json',
            },
            'F8_Q_is_design_variable': {
                'finding': 'B6/B7/B8 是完全因子设计网格，Q_score 为设计因子非测量值',
                'evidence': 'B6=9x5x8=360 完整；B7=9x5x10=450 完整；'
                            'B8=15x10x12=1800 实 1704（缺 96 格）；'
                            'Q_score 仅取 8/10/12 个整数刻度值',
                'consequence': 'Q1 的经验 Q（连续、受域混淆）与 B6-B8 的网格 Q 不是同类对象，'
                               '不能靠线性缩放对齐。此为 Q2 首要探针',
                'source': 'workspace/data/profile_b_scaling.json',
            },
            'F9_bridge_high_tier_tiny': {
                'finding': '桥接高可比样本仅 7 条',
                'evidence': 'C5 43 行（High 7 / Medium 36）；C6 75 行（High 7 / Medium 68）；'
                            '扩展仅增加 Medium 层',
                'consequence': 'Loss-Benchmark 映射实际建立在 7 个可靠点上，'
                               '映射误差须作为独立随机项传播',
                'source': 'workspace/data/profile_c_leaderboard.json',
            },
            'F10_loss_benchmark_sign': {
                'finding': 'Loss 与 Benchmark 均分负相关，符合题设方向',
                'evidence': 'C5 全样本 r=-0.5015；C6 r=-0.5100；'
                            'High 层 r=-0.3975（n=7）；Medium 层 r=-0.49~-0.50',
                'consequence': '方向正确；High 层相关反而弱于 Medium，样本量太小所致，'
                               '不可据此认为 High 层质量更差',
                'source': 'workspace/data/profile_c_leaderboard.json',
            },
            'F11_short_time_window': {
                'finding': 'Q4 的密集时间窗口远短于预测窗口',
                'evidence': 'C1 跨度 2024-06-08 至 2025-03-13 共 278 天（9.1 个月）；'
                            'C3 名义 2019-2025，但 2024 年前仅 24 行'
                            '（2019:1, 2020:1, 2021:2, 2022:7, 2023:13），2024-2025 为 4575 行',
                'consequence': '用约 15 个月密集数据外推 12-24 个月，不确定性必然很宽；'
                               '须报区间而非点值',
                'source': 'workspace/data/profile_c_leaderboard.json',
            },
            'F12_pretrained_subsample_small': {
                'finding': 'C1 的 pretrained 子样本很小',
                'evidence': 'Type 分布：fine-tuned 1785、base merges 1724、chat 718、'
                            'pretrained 275、continuously pretrained 58、multimodal 9、other 7',
                'consequence': '题目要求区分 pretrained 与 chat/finetuned，'
                               '但 pretrained 仅占 6.0%（275/4576），分组建模时须报告该组精度更低',
                'source': 'workspace/data/profile_c_leaderboard.json',
            },
            'F13_c7_match_rate': {
                'finding': 'C7 与 C1 的模型名匹配率 84.1%',
                'evidence': '归一化名称后 37/44 命中；未命中均为 cerebras-gpt 系列'
                            '（属 B2 而非榜单）',
                'consequence': 'L_ctx 取值依据可用；未命中部分不影响 Q3，因 C7 只需提供可行取值集',
                'source': 'workspace/data/profile_c_leaderboard.json',
            },
            'F14_c8_parseability': {
                'finding': 'C8 结构与数据说明一致',
                'evidence': '1863 目录 / 1958 JSON；1860 目录有可解析记录；'
                            '4 个文件截断（同一时间戳 results_2025-02-13T18-27-04.338360.json）；'
                            '每模型任务数 44（1771 个）或 45（85 个）',
                'consequence': '逐任务聚合可行；按目录取最新可解析记录，跳过 4 个截断文件',
                'source': 'workspace/data/profile_c8.json',
            },
        },
        'quality': {
            'missingness': {
                'A_quality_signals': {
                    'A1': '18/51230 行 (0.0351%)，modernbert_reasoning 13 + '
                          'modernbert_professionalism 5，均为整条 6 维向量 NaN',
                    'A2': '0/17523',
                    'A3': '1/203752 (0.0005%)，modernbert_professionalism',
                    'partial_lists': '无（不存在部分 NaN 的向量）',
                },
                'A_mixture_loss': '13 个 Loss 列无缺失；6 对表 index 全对齐',
                'C1': '12/4576 行缺 Submission Date',
                'C4': 'Open model weights? 列 870/3523 空白',
                'C1_license': 'Hub License 1753/4576 空白',
            },
            'duplicates': {'checked': 'A1/A2/A3 字段集唯一（各仅 1 种 schema）',
                           'note': '行级重复未检；id 唯一性待清洗阶段核验'},
            'impossible_values': {
                'mixture_rowsums': '全部在 [0.996, 1.003]，符合数据说明的千分位舍入',
                'Q_score_range': 'B6/B7 ∈ [0.1,1.0]，B8 ∈ [0.05,1.0]，无越界',
            },
            'outliers': {
                'rps_doc_word_count': 'A2 (arxiv) p95=16349 vs A3 (github) p95=1223，'
                                      '域间差异 13 倍，非异常而是文体差异',
                'dsir_*': 'dsir_books/wiki/math 的 AUC 为 0.034/0.035/0.045，'
                          '方向与其他指标相反（对数似然比类指标）',
            },
        },
        'coverage': {
            'rows': {'A_quality_total': 272505, 'A_mixture_rows': 512 + 256 * 2 + 64 + 63 * 2,
                     'B_scaling_rows': 1176 + 1029 + 4000 + 57 + 44 + 360 + 450 + 1704 + 132 + 128,
                     'C_leaderboard_rows': 4576, 'C8_models': 1860},
            'effective_sample_size': {
                'Q1a_domains': 7,
                'Q1a_smallest_domain': {'book': 171},
                'Q1c_train_pairs': 512,
                'Q1c_validation_pairs': {'1m': 256, '60m': 256, '1B': 64},
                'Q2_real_fit_points': 1176,
                'Q2_points_with_Q': {'B6': 360, 'B7': 450, 'B8_calibrated': 984},
                'Q4_bridge_high_tier': 7,
                'Q4_pretrained_models': 275,
            },
            'time_range': {'C1': '2024-06-08 .. 2025-03-13 (278 days)',
                           'C3_nominal': '2019..2025',
                           'C3_dense': '2024..2025 (4575 of 4599 rows)'},
            'time_gaps': {'C1_monthly_min': '2024-07: 174 rows',
                          'C3_pre_2024': '24 rows total across 2019-2023'},
        },
        'distribution_risks': {
            'class_imbalance': {
                'A_domains': 'github 78.44% vs book 0.06%，比值 1250:1',
                'C1_type': 'pretrained 275 vs fine-tuned 1785，比值 1:6.5',
                'bridge_tiers': 'High 7 vs Medium 68（C6），比值 1:9.7',
            },
            'rare_categories': ['book 域 171 条', 'C1 multimodal 9 / other 7',
                                'C3 2019-2021 共 4 行'],
            'high_cardinality': ['C4 57 列', 'C1 Hub License 27 个取值',
                                 'C8 任务键约 44-45 个/模型'],
            'redundancy_warnings': [
                'A1 的 22 指标间存在强相关（待清洗阶段出相关矩阵）',
                'C2 是 C1 的超集（+Epoch 匹配列），不可同时作为独立样本',
                'C9 与 C1 六维等价，已排除',
                'A12/A14 取自 A4 的 train 子集，与训练集非独立',
            ],
            'concentration_metrics': {
                'mixture_top3_mass_median': {'train_1m': 0.879, 'test_1B': 0.691},
                'note': '配方高度集中于少数域，影响交互项的可估性',
            },
        },
        'per_question_readiness': {
            'Q1': {'status': 'ready_with_warnings',
                   'warnings': ['F2 域混淆：Q 有退化为域标签的实质风险，须按域归一化',
                                'F4 A16 仅 6/17 域有质量域对应，限制 Q 引入配比模型的可行性',
                                'F5 配方稀疏，ILR 不可用',
                                'F3 book 域仅 171 条，域级 Q 不确定性大',
                                'F1 列表型标量化规则已定，须在清洗阶段固化']},
            'Q2': {'status': 'ready_with_warnings',
                   'warnings': ['F8 Q 尺度对齐是首要风险：经验 Q 与设计网格 Q 非同类对象',
                                'B6-B8 为半合成且是唯一含 Q 数据，角色须限定',
                                'B10 为估算值，不可参与拟合',
                                '尺度区间：A 为 1M-1B，B1 为 0.07-12B，跨来源统一假设须检验']},
            'Q3': {'status': 'ready',
                   'warnings': ['依赖 Q1/Q2 输出，本身数据需求仅 C7 + 附录 B 参数',
                                'C7 可行 L_ctx 已确认 5 个取值，其中 32768/131072 跨越临界值 30000']},
            'Q4': {'status': 'ready_with_warnings',
                   'warnings': ['F11 密集窗口 ~15 个月，短于 12-24 个月预测窗口',
                                'F9 桥接高可比仅 7 条',
                                'F12 pretrained 仅 275 条（6.0%）',
                                'C3 历史锚点仅 24 行，不足以刻画 2019-2023 趋势',
                                'C4 开源权重列 870 空白，筛选口径须处理缺失']},
        },
        'cleaned_files': [],
        'unresolved_risks': [
            'A18 抽样文本统计尚未执行（HD-3=B 承诺项）',
            'A1/A2/A3 的 id 唯一性与行级重复未核验',
            '22 指标的相关矩阵与共线性诊断未出',
            '22 指标的正/负方向标注表未最终固化（需逐指标语义确认）',
            'C8 逐任务聚合的具体口径未定（取哪些任务、如何标准化）',
        ],
    }

    OUT.write_text(json.dumps(profile, ensure_ascii=False, indent=1), encoding='utf-8')
    n = len(profile['raw_files'])
    print(f'wrote {OUT}')
    print(f'  raw_files tiered: {n}')
    print(f'  key_findings: {len(profile["key_findings"])}')
    print(f'  readiness: ' + ', '.join(
        f'{k}={v["status"]}' for k, v in profile['per_question_readiness'].items()))
    print(f'  unresolved_risks: {len(profile["unresolved_risks"])}')


if __name__ == '__main__':
    main()
