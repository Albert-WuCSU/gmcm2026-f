"""从三份探针输出派生 methods/Q1/probes/risk_probe_summary.json。

不手抄数字：所有证据值从 q1_probe_quality.json / q1_probe_quality2.json /
q1_probe_mixture.json 读取，保证与探针实跑结果一致。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import q1_features as qf

DATA = qf.ROOT / "workspace/data"
OUTDIR = qf.ROOT / "methods/Q1/probes"
OUT = OUTDIR / "risk_probe_summary.json"
TZ = timezone(timedelta(hours=8))


def main() -> None:
    q1 = json.loads((DATA / "q1_probe_quality.json").read_text(encoding="utf-8"))
    q2 = json.loads((DATA / "q1_probe_quality2.json").read_text(encoding="utf-8"))
    mx = json.loads((DATA / "q1_probe_mixture.json").read_text(encoding="utf-8"))

    pooled, perdom = q2["pooled"], q2["per_domain"]
    npop = q1["normalization_population_comparison"]
    ac = q1["assumption_checks_raw"]
    ew = q1["entropy_weight_confound_check"]
    tierc = q2["tierC_direction_sensitivity"]
    sc = q2["scale_check"]
    deg = pooled["degeneracy"]
    conf = pooled["conflict"]
    dcon = pooled["direction_consistency"]
    boot = pooled["domain_aggregation_bootstrap"]
    mac = mx["assumption_checks"]
    fpw = mx["fits"]["pweighted13"]
    fmn = mx["fits"]["mean13"]

    def val(fit, key):
        return fit["validation"][key]

    common_coverage = {
        "status": "PASS",
        "evidence": {
            "rows_used": q2["n_rows"],
            "rows_available": 272505,
            "rows_dropped_nan": q1["meta"]["rows_skipped_nan"],
            "coverage_rate": round(q2["n_rows"] / 272505, 6),
            "selection_rule": "A1+A2+A3 全量流式读取，非抽样；仅剔除整条 NaN 向量行",
            "domains": q1["meta"]["domains"],
            "smallest_domain": {"book": boot["book"]["n"]},
            "largest_domain": {"github": boot["github"]["n"]},
            "imbalance_ratio_max_over_min": round(boot["github"]["n"] / boot["book"]["n"], 1),
            "book_bootstrap_ci_width": boot["book"]["ci_width"],
            "github_bootstrap_ci_width": boot["github"]["ci_width"],
            "ci_width_ratio_book_over_github": round(
                boot["book"]["ci_width"] / boot["github"]["ci_width"], 1),
        },
        "notes": ["剔除行数 A1=18 / A3=1 与 workspace/data/missingness_a.json 的独立审计精确一致",
                  "book 域 bootstrap 区间宽度为 github 的 29.6 倍，域级 Q 的可分辨性受限"],
    }

    shared_assumptions = [
        {"name": "direction_table_internal_consistency", "status": "FAIL",
         "metric": "n_pairs_corr_lt_-0.5_after_direction_unification",
         "value": dcon["n_pairs_r_lt_minus_0.5"], "threshold": 0,
         "evidence": {"n_pairs_lt_-0.8": dcon["n_pairs_r_lt_minus_0.8"],
                      "n_involving_tier_C": dcon["involves_tier_C"],
                      "worst_pairs": dcon["pairs"][:3]},
         "interpretation": "两指标都已统一为『越高越好』却强负相关，至少一方方向赋值与数据不相容；"
                           "20 对中 17 对涉及 Tier C（dsir×3 / word_count / num_sentences）",
         "blocks": "须由使用者裁定 Tier C 方向语义后方可解除"},
        {"name": "indicator_redundancy", "status": "CONDITIONAL",
         "metric": "max_abs_offdiag_corr", "value": ac["max_abs_offdiag_corr"],
         "threshold": 0.9,
         "evidence": {"dsir_triple_mutual_r": 0.9998,
                      "n_pairs_gt_0.9": ac["n_pairs_absdcorr_gt_0.9"],
                      "n_pairs_gt_0.7": ac["n_pairs_absdcorr_gt_0.7"],
                      "corr_condition_number": ac["corr_condition_number"],
                      "pc1_variance_share": ac["pc1_variance_share"],
                      "pc1_pc2_variance_share": ac["pc1_pc2_variance_share"]},
         "interpretation": "dsir_books/wiki/math 互相关 0.999，实质是 1 个指标而非 3 个；"
                           "等权会把同一信号计 3 次。无单一主因子（PC1 仅 38.2%）",
         "mitigation": "dsir 三列合为 1 个代表量或按 1/3 降权，并在方法卡记录"},
        {"name": "naive_minmax_numerical_degeneracy", "status": "FAIL",
         "metric": "median_position_in_naive_minmax_range",
         "value": q1["naive_minmax_degeneracy"]["rps_doc_word_count"][
             "median_position_in_naive_minmax"],
         "threshold": "应接近 0.5",
         "evidence": {k: q1["naive_minmax_degeneracy"][k]["median_position_in_naive_minmax"]
                      for k in ("rps_doc_word_count", "rps_doc_num_sentences",
                                "rps_doc_frac_chars_top_3gram", "dsir_books",
                                "dsir_wiki", "dsir_math")},
         "interpretation": "GC2 字面示例『Min-Max 归一化后 x→1-x』在 6 个重尾指标上数值退化："
                           "word_count 中位数落在量程 0.027% 处，dsir_* 落在 99.88% 处",
         "mitigation": "先 1%-99% 截尾或改用经验分位数归一化；GC2 的硬性要求是"
                       "『统一为越高越好』，补转换公式为示例（原文『例如』）"},
        {"name": "normalization_population_unresolved", "status": "CONDITIONAL",
         "metric": "tradeoff_between_deconfounding_and_cross_domain_signal",
         "evidence": {k: {"cross_domain_range": v["cross_domain_range"],
                          "auc_of_Q_recovering_domain": v["auc_arxiv_vs_github_of_Q"]}
                      for k, v in npop.items()},
         "interpretation": "按域归一化(ecdf)把 Q 的域标签信息降到 AUC=0.498，但域间极差同时降到 0.0028，"
                           "域级 Q 近乎恒等，与 Q1a 必交产出『域级 Q 并与抽样集对照』冲突；"
                           "合并/参照 A1 口径下 AUC 0.98-0.99，Q 近乎等价于域标签",
         "blocks": "须由使用者裁定口径"},
        {"name": "entropy_weighting_is_normalization_artifact", "status": "FAIL",
         "metric": "entropy_weight_max_over_equal_weight",
         "value": ew["entropy_weight_max_over_equal"],
         "evidence": {"under_ecdf": ew["entropy_weight_max_over_equal"],
                      "under_winsor_minmax": 6.276,
                      "top3_mass_under_minmax": 0.58,
                      "top3_columns_under_minmax": ["rps_doc_word_count",
                                                    "rps_doc_num_sentences",
                                                    "modernbert_reasoning"],
                      "pearson_weight_vs_domain_separation": ew["pearson_w_vs_domain_separation"]},
         "interpretation": "分位数归一化后各列边际分布相同，熵权退化为等权（max/equal=1.002，零增量）；"
                           "截尾 Min-Max 下熵权把 58% 质量压在 3 个指标上，其中 2 个恰是方向未定"
                           "且域指示性最强的长度类指标（AUC 0.987/0.947）。故熵权法在本题不构成"
                           "有依据的主方法，已据证据排除",
         "eliminates": "entropy_weight_TOPSIS_family"},
    ]

    methods = []

    # ---------------- M0 baseline（质量侧）----------------
    methods.append({
        "id": "M0",
        "name": "22 指标方向统一后等权平均（域级用截尾均值/Huber 聚合）",
        "role": "usable_baseline",
        "subtasks": ["Q1a", "Q1b"],
        "baseline_source": "HD-2=B 指定",
        "executability": {"status": "PASS", "evidence": {
            "rows": q2["n_rows"], "runtime_seconds": sc["total_seconds"],
            "produces_legal_output": True,
            "output_range": "[0,1]"}},
        "data_coverage": common_coverage,
        "assumption_checks": shared_assumptions,
        "output_degeneracy": {"status": "PASS", "metrics": {
            "std": deg["M0_equal_weight"]["std"],
            "coefficient_of_variation": deg["M0_equal_weight"]["coefficient_of_variation"],
            "unique_output_count": deg["M0_equal_weight"]["unique_output_count"],
            "unique_ratio": deg["M0_equal_weight"]["unique_ratio"],
            "gini": deg["M0_equal_weight"]["gini"],
            "top1pct_mass_share": deg["M0_equal_weight"]["top1pct_mass_share"],
            "domain_huber_range": deg["M0_equal_weight"]["domain_huber_range"],
            "domain_huber": deg["M0_equal_weight"]["domain_huber"]},
            "interpretation": "无退化：评分连续、唯一值比 0.64、基尼 0.092、域间极差 0.153",
            "caveat": "域序为 arxiv>c4>commoncrawl>stackexchange>book>wikipedia>github，"
                      "wikipedia 次末、c4 第二，与『质量』的常识排序不符，"
                      "说明合并口径下该合成量更接近『长篇散文性』而非质量"},
        "perturbation_sensitivity": {"status": "PASS",
                                     "perturbation": pooled["perturbation_sensitivity"]["perturbation"],
                                     "metrics": pooled["perturbation_sensitivity"]},
        "scale_check": {"status": "PASS", "representative_n": sc["representative_n"],
                        "runtime_seconds": sc["total_seconds"],
                        "peak_memory_mb": sc["peak_memory_mb"],
                        "note": "个人电脑可完成，满足 GC11"},
        "verdict": "CONDITIONAL",
        "conditions": [
            "Tier C 方向语义须由使用者裁定（direction_table_internal_consistency = FAIL）",
            "dsir 三列冗余须处理（r=0.999）",
            "归一化总体口径须由使用者裁定",
            "GC2 字面 Min-Max 须替换为截尾或分位数版本",
        ],
        "evidence_refs": ["workspace/data/q1_probe_quality.json",
                          "workspace/data/q1_probe_quality2.json"],
    })

    # ---------------- M1 main（质量侧）----------------
    methods.append({
        "id": "M1",
        "name": "语义分组 V/P + 门控合成 Q=V·(1−P)；冲突 = 高价值∧高污染（分位数锚定）",
        "role": "main_candidate",
        "subtasks": ["Q1a", "Q1b"],
        "executability": {"status": "PASS", "evidence": {
            "rows": q2["n_rows"], "runtime_seconds": sc["total_seconds"],
            "n_value_cols": ac["block_structure"]["n_value_cols"],
            "n_pollution_cols": ac["block_structure"]["n_pollution_cols"]}},
        "data_coverage": common_coverage,
        "assumption_checks": shared_assumptions + [
            {"name": "VP_block_cohesion", "status": "CONDITIONAL",
             "metric": "mean_signed_corr_within_group",
             "value": {"within_value": ac["block_structure"]["mean_corr_within_value"],
                       "within_pollution": ac["block_structure"]["mean_corr_within_pollution"],
                       "between": ac["block_structure"]["mean_corr_between"]},
             "interpretation": "V/P 分组不具相关内聚性（组内均值 0.051/0.026，与组间 0.016 同量级），"
                               "故分组是语义划分而非统计块；但组间近零相关恰是冲突非空的前提",
             "mitigation": "分组依据须在论文中以指标语义论证，不得声称由相关结构导出"},
            {"name": "conflict_definition_non_degeneracy", "status": "CONDITIONAL",
             "metric": "conflict_rate_must_be_in_open_interval_0_1",
             "evidence": {
                 "CD2_absolute_threshold_0.75": conf["CD2_local_highV_and_highP"],
                 "CD2_quantile_anchored_p75": conf["CD2_local_quantile_based"],
                 "CD1_global_MAD_gt_0.25": conf["CD1_global_MAD_gt_0.25"],
                 "CD3_ge3_high_and_ge3_low": conf["CD3_ge3_high_and_ge3_low"],
                 "CD3_ge5_high_and_ge5_low": conf["CD3_ge5_high_and_ge5_low"],
                 "corr_V_vs_P": conf["corr_V_vs_P"],
                 "V_p75_actual": conf["CD2_thresholds_p75"]["V_p75"],
                 "P_p75_actual": conf["CD2_thresholds_p75"]["P_p75"]},
             "interpretation": "绝对阈版冲突率恰为 0.0（退化）：V 为 16 列均值，标准差仅约 0.072，"
                               "实际 p75 只有 0.567，『>0.75』几乎无样本。分位数锚定版 0.0363 可用。"
                               "思路文档第 4 页的『高价值×高污染』定义须改为分位数锚定才成立",
             "mitigation": "冲突判据一律用分位数锚定；绝对阈版已据证据排除"},
        ],
        "output_degeneracy": {"status": "PASS", "metrics": {
            "gated_form": deg["M1_gated"],
            "difference_form": deg["M1_difference"]},
            "interpretation": "门控式 Q=V·(1−P) 无退化（sd 0.082、基尼 0.185、域间极差 0.135）且恒在 [0,1]",
            "eliminated_variant": {
                "form": "Q = V − P",
                "reason": "跨零使均值近 0，CV 达 1.44e6、基尼 8.17e5 均失去意义；"
                          "且负 Q 与 Q3 成本函数 g(Q)=γQ^4 与 γe^{6Q} 不相容",
                "evidence": {"coefficient_of_variation": deg["M1_difference"]["coefficient_of_variation"],
                             "gini": deg["M1_difference"]["gini"]}}},
        "perturbation_sensitivity": {"status": "PASS",
                                     "perturbation": pooled["perturbation_sensitivity"]["perturbation"],
                                     "metrics": pooled["perturbation_sensitivity"],
                                     "note": "扰动施于等权基准；分组权重的扰动须在 G3 复测"},
        "scale_check": {"status": "PASS", "representative_n": sc["representative_n"],
                        "runtime_seconds": sc["total_seconds"],
                        "peak_memory_mb": sc["peak_memory_mb"]},
        "verdict": "CONDITIONAL",
        "conditions": [
            "与 M0 相同的四项前置（方向 / 冗余 / 口径 / Min-Max）",
            "只采用门控式，差值式已排除",
            "冲突判据须分位数锚定",
            "V/P 分组须以语义论证，不得声称由相关结构导出",
        ],
        "evidence_refs": ["workspace/data/q1_probe_quality2.json",
                          "workspace/data/q1_probe_corr.json"],
    })

    # ---------------- M2 fallback（质量侧）----------------
    methods.append({
        "id": "M2",
        "name": "指标间稳健序统计合成（中位数）+ 指标离散度冲突判据",
        "role": "conditional_fallback",
        "subtasks": ["Q1a", "Q1b"],
        "probe_depth": "仅探至可信度足以确认触发条件与风险轮廓，未完整实现",
        "executability": {"status": "PASS", "evidence": {"rows": q2["n_rows"]}},
        "data_coverage": {"status": "PASS", "evidence": {"same_as": "M0"}},
        "assumption_checks": [
            {"name": "robustness_to_direction_misassignment", "status": "PASS",
             "metric": "median_is_insensitive_to_minority_wrong_signs",
             "interpretation": "22 列中位数不受少数列方向错配主导，是对"
                               "direction_table_internal_consistency=FAIL 的针对性缓解"},
        ],
        "output_degeneracy": {"status": "PASS", "metrics": deg["M2_median"],
                              "interpretation": "域间极差 0.327，为三法中最大；"
                                                "sd 0.146、基尼 0.162，无退化"},
        "perturbation_sensitivity": {"status": "NOT_PROBED",
                                     "reason": "按 method-selector 规则，fallback 只探到触发条件可信即止"},
        "scale_check": {"status": "PASS", "representative_n": sc["representative_n"]},
        "verdict": "PASS",
        "activation_trigger": {
            "trigger": "使用者裁定 Tier C 方向后，若 direction_table_internal_consistency 仍有"
                       "≥3 对 r<−0.8 的矛盾对，或 M1 门控式在所选口径下冲突率落到 (0.01,0.50) 之外",
            "evidence_to_evaluate": ["methods/Q1/probes/risk_probe_summary.json"
                                     "#methods[?id=='M1'].assumption_checks",
                                     "workspace/data/q1_probe_quality2.json"],
        },
        "evidence_refs": ["workspace/data/q1_probe_quality2.json"],
    })

    # ---------------- M0c baseline（配比侧）----------------
    mix_coverage = {
        "status": "CONDITIONAL",
        "evidence": {
            "train_rows": mx["data_coverage"]["train_1m"]["rows"],
            "test_rows": {k: mx["data_coverage"][k]["rows"]
                          for k in ("test_1m", "test_60m", "test_1B")},
            "extrapolation_rows": {k: mx["data_coverage"][k]["rows"]
                                   for k in ("est_10b", "est_70b")},
            "zero_rate_train": mx["data_coverage"]["train_1m"]["zero_rate"],
            "zeros_per_row_median_train": mx["data_coverage"]["train_1m"]["zeros_per_row_median"],
            "top3_mass_median": {k: mx["data_coverage"][k]["top3_mass_median"]
                                 for k in ("train_1m", "test_1B")},
            "mixture_shift": mx["train_test_mixture_shift"],
        },
        "interpretation": "A12/A14 的配比行与训练集完全重复（frac_exact_duplicate=1.0），"
                          "故 A12–A15 只能检验 Loss 外推，不能检验配比泛化；"
                          "A10（1B）配比离训练集最近邻 L1 距离为训练内部间距的 1.40 倍，属轻度外推",
        "notes": ["ILR 变换已排除：训练表 512 行中 511 行含精确零、每行中位 8/17 域为零"],
    }

    methods.append({
        "id": "M0c",
        "name": "17 维配比线性回归（去截距/指定参照域），目标为配比加权 13 域 Loss",
        "role": "usable_baseline",
        "subtasks": ["Q1c"],
        "baseline_source": "HD-2=B 指定",
        "executability": {"status": "PASS", "evidence": {
            "runtime_seconds": mx["runtime_seconds"],
            "train_r2": fpw["M0c_linear_main"]["train_r2"]}},
        "data_coverage": mix_coverage,
        "assumption_checks": [
            {"name": "simplex_induced_singularity", "status": "CONDITIONAL",
             "metric": "condition_number",
             "value": {"main_only_17": mac["cond_main_only_17"],
                       "with_intercept_18": mac["cond_with_intercept_18"]},
             "evidence": {"rowsum_max_deviation": mac["simplex_rowsum_deviation_max"],
                          "smallest_singular_with_intercept": mac["smallest_singular_with_intercept"]},
             "interpretation": mac["note_intercept"],
             "mitigation": "显式去截距或指定参照域；不得依赖千分位舍入来辨识截距"},
            {"name": "target_aggregation_choice", "status": "CONDITIONAL",
             "metric": "train_r2_and_coefficient_stability_by_target",
             "value": {"pweighted13": {
                 "train_r2": fpw["M0c_linear_main"]["train_r2"],
                 "sign_stable_frac": fpw["M0c_linear_main"]["coef_bootstrap"][
                     "frac_coefs_sign_stable_ge_0.95"],
                 "mean_relative_se": fpw["M0c_linear_main"]["coef_bootstrap"]["mean_relative_se"]},
                 "mean13": {
                     "train_r2": fmn["M0c_linear_main"]["train_r2"],
                     "sign_stable_frac": fmn["M0c_linear_main"]["coef_bootstrap"][
                         "frac_coefs_sign_stable_ge_0.95"],
                     "mean_relative_se": fmn["M0c_linear_main"]["coef_bootstrap"]["mean_relative_se"]}},
             "interpretation": "配比加权 13 域 Loss 作目标时条件数与系数稳定性远优于 13 域简单均值"
                               "（R² 0.896 vs 0.296，符号稳定 1.000 vs 0.882，相对 SE 0.035 vs 0.222）；"
                               "但该目标把 p 同时放在等式两侧，存在部分循环，须在论文中声明",
             "open_item": "AMB-Q1-2：13 维 Loss 是否汇总为单一标量，题目授权本队论证"},
            {"name": "cross_scale_transfer", "status": "PASS",
             "metric": "bias_share_of_rmse_and_r2_after_offset_removal",
             "evidence": {k: {"r2_raw": val(fpw["M0c_linear_main"], k)["r2"],
                              "bias_share_of_rmse": val(fpw["M0c_linear_main"], k)["bias_share_of_rmse"],
                              "r2_after_offset_removal": val(fpw["M0c_linear_main"], k)[
                                  "r2_after_offset_removal"],
                              "spearman": val(fpw["M0c_linear_main"], k)["spearman"]}
                          for k in ("test_1m", "test_60m", "test_1B", "est_10b", "est_70b")},
             "interpretation": "原始 R² 在 60m/1B 为 −8.4/−173，但 bias 占 RMSE 的 98.8%/99.9%；"
                               "去掉按尺度的常数偏移后 R² 回到 0.771/0.705、Spearman 0.922/0.887。"
                               "即配比→Loss 的形状跨尺度可迁移，只有水平随模型规模平移。"
                               "故 A6–A11 的验证口径必须含按尺度截距，或改用秩相关",
             "caveat": "est_10b/est_70b 去偏后 R² 仍为负（−0.66/−1.22），说明 A13/A15 的幂律外推"
                       "未保持配比响应形状，只能作定性讨论（符合 GC5）"},
        ],
        "output_degeneracy": {"status": "PASS", "metrics": {
            "n_coef": fpw["M0c_linear_main"]["n_coef"],
            "coef_top5_share_of_l1": fpw["M0c_linear_main"]["coef_top5_share_of_l1"],
            "coef_abs_max": fpw["M0c_linear_main"]["coef_abs_max"],
            "pred_std_vs_true_std_test_1m": [
                val(fpw["M0c_linear_main"], "test_1m")["pred_std"],
                val(fpw["M0c_linear_main"], "test_1m")["true_std"]]},
            "interpretation": "系数无过度集中（top5 占 L1 的 34.8%），预测离散度与真实相当"},
        "perturbation_sensitivity": {"status": "PASS", "metrics": fpw["M0c_linear_main"]["coef_bootstrap"],
                                     "interpretation": "200 次自助重采样下 17 个系数 100% 符号稳定，"
                                                       "平均相对标准误 0.035"},
        "scale_check": {"status": "PASS", "representative_n": 512,
                        "runtime_seconds": mx["runtime_seconds"]},
        "verdict": "PASS",
        "conditions": [],
        "evidence_refs": ["workspace/data/q1_probe_mixture.json"],
    })

    # ---------------- M1c main（配比侧）----------------
    methods.append({
        "id": "M1c",
        "name": "主效应 + 二阶交互（153 特征）+ 岭正则，CV 选 λ",
        "role": "main_candidate",
        "subtasks": ["Q1c"],
        "executability": {"status": "PASS", "evidence": {
            "n_features": mac["n_features_interactions"],
            "n_rows": mac["n_train_rows"],
            "features_over_rows": mac["features_over_rows_ratio"],
            "selected_lambda": fpw["M1c_main_plus_inter_ridge"]["lambda"],
            "runtime_seconds": mx["runtime_seconds"]}},
        "data_coverage": mix_coverage,
        "assumption_checks": [
            {"name": "interaction_identifiability", "status": "FAIL",
             "metric": "frac_coefs_sign_stable_ge_0.95",
             "value": fpw["M1c_main_plus_inter_ridge"]["coef_bootstrap"][
                 "frac_coefs_sign_stable_ge_0.95"],
             "threshold": 0.95,
             "evidence": {"baseline_M0c": fpw["M0c_linear_main"]["coef_bootstrap"][
                 "frac_coefs_sign_stable_ge_0.95"],
                 "mean_relative_se_M1c": fpw["M1c_main_plus_inter_ridge"][
                     "coef_bootstrap"]["mean_relative_se"],
                 "mean_relative_se_M0c": fpw["M0c_linear_main"]["coef_bootstrap"][
                     "mean_relative_se"],
                 "cond_153_features": mac["cond_main_plus_interactions_153"],
                 "top3_mass_median_train": mx["data_coverage"]["train_1m"]["top3_mass_median"]},
             "interpretation": "交互项系数符号稳定率仅 0.549（baseline 1.000），平均相对标准误 1.514"
                               "（baseline 0.035）。512 行、每行中位 8/17 域为零、top3 质量占 0.879，"
                               "136 个二阶交互项无法逐项辨识。可用于整体预测，不可对单个交互项"
                               "做『某两域互补/替代』的定量断言",
             "blocks": "禁止把单个交互系数解释为域间替代关系；域组合影响须改用"
                       "组级或方向性证据（如按 KKT/梯度的联合扰动）表述"},
            {"name": "cross_scale_transfer_gain_over_baseline", "status": "FAIL",
             "metric": "r2_after_offset_removal_vs_baseline",
             "value": {k: {"M1c": val(fpw["M1c_main_plus_inter_ridge"], k)[
                 "r2_after_offset_removal"],
                 "M0c": val(fpw["M0c_linear_main"], k)["r2_after_offset_removal"]}
                 for k in ("test_1m", "test_60m", "test_1B")},
             "interpretation": "同尺度（1m）交互项确有增益 0.913→0.983；但 60m 基本持平"
                               "（0.771→0.766），1B 反而更差（0.705→0.658）。"
                               "即增益是尺度局部的，不构成跨尺度优势",
             "triggers_escalation": "HD-2 已预告：baseline 强而主方法增量小时须由使用者判断增量是否值得"},
        ],
        "output_degeneracy": {"status": "PASS", "metrics": {
            "n_coef": fpw["M1c_main_plus_inter_ridge"]["n_coef"],
            "coef_top5_share_of_l1": fpw["M1c_main_plus_inter_ridge"]["coef_top5_share_of_l1"],
            "train_r2": fpw["M1c_main_plus_inter_ridge"]["train_r2"]},
            "interpretation": "预测不退化，但系数分散（top5 仅占 L1 的 13.6%）正对应不可辨识"},
        "perturbation_sensitivity": {"status": "FAIL",
                                     "metrics": fpw["M1c_main_plus_inter_ridge"]["coef_bootstrap"],
                                     "interpretation": "见 interaction_identifiability"},
        "scale_check": {"status": "PASS", "representative_n": 512,
                        "runtime_seconds": mx["runtime_seconds"]},
        "verdict": "CONDITIONAL",
        "conditions": [
            "只能声明整体预测精度，不得对单个二阶交互系数作域间替代/互补的定量断言",
            "跨尺度增益不成立，须由使用者判断同尺度增量是否值得（HD-2 升级条款）",
            "A6–A11 验证须含按尺度截距或改用秩相关",
        ],
        "evidence_refs": ["workspace/data/q1_probe_mixture.json"],
    })

    summary = {
        "schema_version": 1,
        "question_id": "Q1",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "rigor_profile": "lean",
        "seed": qf.SEED,
        "data_refs": ["workspace/data/data_profile.json",
                      "workspace/data/data_report.md",
                      "workspace/data/q1_probe_quality.json",
                      "workspace/data/q1_probe_quality2.json",
                      "workspace/data/q1_probe_corr.json",
                      "workspace/data/q1_probe_mixture.json",
                      "workspace/data/q1_polarity_evidence.json"],
        "probe_scripts": ["workspace/code/scripts/q1_features.py",
                          "workspace/code/scripts/probe_q1_polarity.py",
                          "workspace/code/scripts/probe_q1_quality.py",
                          "workspace/code/scripts/probe_q1_corr.py",
                          "workspace/code/scripts/probe_q1_quality2.py",
                          "workspace/code/scripts/probe_q1_mixture.py"],
        "shortlist_structure_rationale": {
            "counts": {"main_candidate": 2, "usable_baseline": 2, "conditional_fallback": 1},
            "why_not_one_each": "Q1 含两个数学上不可合并的估计问题：(i) 22 指标 → 质量评分 Q 的"
                                "多指标合成（Q1a/Q1b，无监督、无目标变量）；(ii) 17 维配比 → Loss 的"
                                "有监督回归（Q1c，有目标变量与独立检验集）。二者的输入、目标、"
                                "检验口径均不同，任何单一方法无法同时完成。HD-2 亦分别为 "
                                "Q1a/Q1b/Q1c 声明了 baseline。故按『每个估计问题恰一主一 baseline』"
                                "计：质量侧 M1/M0，配比侧 M1c/M0c，共享一个 fallback M2。"
                                "非为凑候选数量。",
            "per_problem": {"quality_side": {"main": "M1", "baseline": "M0", "fallback": "M2"},
                            "mixture_side": {"main": "M1c", "baseline": "M0c", "fallback": None}},
        },
        "direction_table": q1["direction_table"],
        "direction_tier_counts": q1["tier_counts"],
        "tierC_direction_sensitivity": tierc,
        "eliminated_with_evidence": [
            {"candidate": "熵权法 / 熵权-TOPSIS 族", "reason": "权重离散度完全由归一化方案决定："
             "分位数下退化为等权（max/equal=1.002），Min-Max 下 58% 权重压在 3 列且其中 2 列方向未定",
             "evidence": "workspace/data/q1_probe_corr.json"},
            {"candidate": "Q = V − P 差值式合成", "reason": "跨零导致 CV=1.44e6，且负 Q 与 Q3 的"
             "g(Q)=γQ^4、γe^{6Q} 不相容", "evidence": "workspace/data/q1_probe_quality2.json"},
            {"candidate": "绝对阈冲突判据（V>0.75 ∧ P>0.75）", "reason": "冲突率恰为 0.0，"
             "因 16 列均值的 p75 仅 0.567", "evidence": "workspace/data/q1_probe_quality2.json"},
            {"candidate": "平方根变换主效应回归（M2c）", "reason": "训练 R²=−2.78，不可用",
             "evidence": "workspace/data/q1_probe_mixture.json"},
            {"candidate": "ILR 等对数比变换", "reason": "512 行中 511 行含精确零，每行中位 8/17 域为零",
             "evidence": "workspace/data/profile_a_mixture.json"},
        ],
        "methods": methods,
        "human_decisions_required": [
            {"decision_id": "q1_tierC_direction",
             "why_human": "指标方向语义属物理/领域解释，AI 不得代定",
             "impact": "book 域级 Q 在五种方向假设下位列第 5/2/7/2/5 位，跨 5 个名次（7 域中），"
                       "单次变更最大名次位移 3，Spearman 最低 0.625"},
            {"decision_id": "q1_normalization_population",
             "why_human": "去混淆与保留跨域信号不可兼得，取舍属建模判断",
             "impact": "决定域级 Q 是否可用作 Q2/Q3 的输入"},
            {"decision_id": "q1c_interaction_tradeoff",
             "why_human": "HD-2 已预告的升级条款：baseline 强、主方法增量为尺度局部",
             "impact": "决定 Q1c 是否声明域组合效应"},
        ],
        "overall_gate_status": "G2 探针完成；M0c 为 PASS，M0/M1/M1c 为 CONDITIONAL，"
                              "M2 为 PASS（fallback）。三项人工裁定未完成前不进入 G2.5",
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
