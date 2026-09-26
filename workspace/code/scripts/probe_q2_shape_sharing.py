"""P8：A/alpha/B 是否跨源可共享（P1 只查过 E）。

判据的诚实说明（不美化时点）：
  本探针起因于 G3 实现中发现两个 gamma（stage2 = 0.9659，联合 WLS = 0.7968）。
  三个参数的数值是在**调试中先看到的**，故本判据不是盲设。
  为使判据仍具决策相关性，判据按「对 gamma 的影响」而非「参数本身差多少」来定义：

  预声明判据：强制共享 A/alpha/B 造成的 gamma 位移，若小于 gamma 自助 95% 区间宽度的 50%，
              则共享可接受；否则判 FAIL、须用来源专属形状参数。
  理由：gamma 是本问的核心可报量，判据应挂在它的不确定性尺度上，而不是挂在中间参数的相对差上。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code/Q2"))
import q2_common as C  # noqa: E402

OUT = ROOT / "workspace/data/q2_probe_shape_sharing.json"
B_BOOT = 400


def main() -> None:
    b1, b7 = C.load_nd("B1"), C.load_b7()
    p0 = C.fit_classic(b1["N"], b1["D"], b1["L"])
    beta = p0["beta"]

    # 路线 A：来源专属形状参数（B7 自有 A/alpha/B，仅 beta 继承 B1）
    pa = C.fit_gamma_on_b7(b7["N"], b7["D"], b7["Q"], b7["L"], beta)
    rng = np.random.default_rng(C.SEED)
    ga = []
    for _ in range(B_BOOT):
        idx = C.boot_indices(np.arange(b7["n"]), rng, "row")
        try:
            ga.append(C.fit_gamma_on_b7(b7["N"][idx], b7["D"][idx], b7["Q"][idx], b7["L"][idx],
                                        beta, seed=int(rng.integers(1e9)))["gamma"])
        except Exception:
            continue
    ci_a = C.ci95(np.array(ga))
    width = ci_a[1] - ci_a[0]

    # 路线 B：强制共享 A/alpha/B（联合 WLS，残差法 sigma）
    s7 = pa["rmse"]
    pb = C.fit_joint_wls(b1, b7, p0["rmse"], s7, with_Q=True)

    shift = abs(pa["gamma"] - pb["gamma"])
    thresh = 0.5 * width
    res = {
        "schema_version": 1, "probe_id": "P8_shape_param_cross_source_sharing",
        "load_bearing_risk": ("P1 只检验了 E 的跨源可共享性。若 A/alpha/B 也不可共享，"
                              "则联合 WLS 中被 B1 钉死的形状参数会迫使 gamma 吸收 B7 的形状失配，"
                              "使 gamma 失去『Q 的有效数据量指数』这一解释"),
        "criterion_timing_disclosure": ("参数数值在调试中先被观察到，本判据非盲设；"
                                        "故判据改挂在 gamma 的自助区间尺度上以保持决策相关性"),
        "predeclared_criterion": "强制共享造成的 gamma 位移 < gamma 自助 95% 区间宽度的 50% 才可共享",
        "route_A_source_specific_shape": {
            "gamma": pa["gamma"], "gamma_ci95": ci_a, "ci_width": float(width),
            "E_B7": pa["E_B7"], "A": pa["A"], "alpha": pa["alpha"], "B": pa["B"],
            "rmse_B7": pa["rmse"], "n_boot_ok": len(ga),
        },
        "route_B_shared_shape": {
            "gamma": pb["gamma"], "A": pb["A"], "alpha": pb["alpha"], "B": pb["B"],
            "E_B1": pb["E_B1"], "E_B7": pb["E_B7"],
            "rmse_B1": pb["rmse_B1"], "rmse_B7": pb["rmse_B7"],
        },
        "shape_param_discrepancy": {
            "A_ratio_B7_over_B1": float(pa["A"] / p0["A"]),
            "alpha_B7": pa["alpha"], "alpha_B1": p0["alpha"],
            "alpha_absolute_difference": float(abs(pa["alpha"] - p0["alpha"])),
            "B_ratio_B7_over_B1": float(pa["B"] / p0["B"]),
        },
        "gamma_shift": float(shift),
        "threshold": float(thresh),
        "shared_shape_admissible": bool(shift < thresh),
        "shift_as_fraction_of_ci_width": float(shift / width) if width > 0 else None,
        "rmse_B7_penalty_of_sharing": float(pb["rmse_B7"] - pa["rmse"]),
        "verdict": "PASS" if shift < thresh else "FAIL",
        "consequence": ("若 FAIL：gamma 须取来源专属形状参数下的值（路线 A），"
                        "且『B1 与 B7 共享 A/alpha/B』不得作为隐含假设使用。"
                        "连带后果：除 beta 外几乎所有参数都来源专属 ⇒ 裁定3=B 的联合 WLS "
                        "在数值上退化为『B1 定 beta、B7 定 gamma』的两段式，"
                        "WLS 机制本身并非错误，只是在该参数结构下无实质作用 —— 须如实说明"),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("gamma_shift", "threshold", "shared_shape_admissible",
                                          "shift_as_fraction_of_ci_width", "verdict",
                                          "rmse_B7_penalty_of_sharing")},
                     ensure_ascii=False, indent=1))
    print("route_A gamma=%.4f ci=%s | route_B gamma=%.4f" % (
        pa["gamma"], [round(x, 4) for x in ci_a], pb["gamma"]))
    print("WROTE", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
