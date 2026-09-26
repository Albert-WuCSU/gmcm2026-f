"""Q3 G4 补算(裁定 q3_result_verdict = 1B / q3_stability_verdict = 2B)。

两件：
  (1) Q0 敏感性：Q0 现取 0.35，run_summary.Q0_spec 明写「未经使用者裁定,可被否决」。
      在 Q1 实测域级 Q 范围 [0.223306, 0.381496] 上扫 5 个取值，看 Q*/loss/转移位置是否移动。
  (2) 题目「或改进 g(Q)」部分：现缺。本脚本**计算三个候选第四类 g**，
      但**不自选**——具体形式属建模判断，须由使用者裁定后采用。

预声明判据（执行前写定）：
  Q0 敏感性判据：若跨 Q0 范围的最优 Q* 极差 > 0.10，或转移位置 log10 C 移动 > 0.10，
                 则 Q0 是承重参数，须在论文显式报该敏感性；否则记「Q0 在实测范围内不影响结构结论」。
  第四类 g 判据：不做通过/不通过判定——题目只要求「讨论」与「或改进」，
                 故只报三个候选的 Q*、loss、转移位置与成本份额，供使用者选择。

只写新文件，不改任何已评审代码（自定义 g 通过 Model 子类注入，不触碰 q3_common）。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "code/Q3"))
import q3_common as C            # noqa: E402
import q3_optimize_main as M     # noqa: E402
from q3_common import ETA, L_CTX_DEFAULT, Model  # noqa: E402

OUT = ROOT / "results/Q3/experiments/round1/metrics/q3_supplement_Q0_and_4th_g.json"

Q0_SCAN = [0.223306, 0.25, 0.30, 0.35, 0.381496]     # 端点 = Q1 实测域级 Q 范围
Q0_CRIT_Q = 0.10
Q0_CRIT_LOG10C = 0.10


class ModelG(Model):
    """自定义第四类 g(Q)：只替换含 g 或 g' 的四处置，其余(分支枚举/KKT/乘子结构)沿用。"""

    def __init__(self, law, Q0, g, gp, name, L_ctx=L_CTX_DEFAULT):
        super().__init__(law, Q0=Q0, L_ctx=L_ctx, form="exponential")
        self._g, self._gp, self.gname = g, gp, name

    def dg(self, Q):
        return max(self._g(Q) - self._g(self.Q0), 0.0)

    def R2(self, N_B, Q):
        return self.ga * (self.k * N_B * 1e9 + self.dg(Q)) - Q * self._gp(Q)

    def N_from_R2(self, Q):
        v = Q * self._gp(Q) / self.ga - self.dg(Q)
        return v / (self.k * 1e9) if v > 0 else None

    def multipliers(self, N_B, D_B, Q):
        S = D_B * Q ** self.ga
        lam = (self.al * self.A * N_B ** (-self.al - 1.0)) / (self.k * D_B * 1e18)
        dQ_benefit = self.be * self.ga * self.B * S ** (-self.be) / Q
        dQ_cost = lam * D_B * 1e9 * self._gp(Q)
        return {"lambda": float(lam),
                "mu_upper": float(dQ_benefit - dQ_cost),
                "nu_lower": float(dQ_cost - dQ_benefit)}

    def cost_parts(self, N_B, D_B, Q):
        N, D = N_B * 1e9, D_B * 1e9
        return {"C_train": 6.0 * N * D, "C_Q": D * self.dg(Q),
                "C_attn": ETA * N * D * self.L_ctx}

    def _r2_rel(self, N_B, Q, branch):
        """必须一并覆盖：父类此方法直接用模块级 g_prime(Q, self.form)，
        若只覆盖 R2/N_from_R2，则审计口径与求解口径不一致，
        会把「自定义 g' 与指数型 g' 之差」误报成 KKT 未过（实测曾出现 0.24/0.56 的假残差）。"""
        if branch != "interior":
            return None
        a = self.ga * (self.k * N_B * 1e9 + self.dg(Q))
        b = Q * self._gp(Q)
        return float(abs(a - b) / max(abs(a), abs(b), 1e-300))


def cand_saturating_exp(q):
    """C1 饱和指数型 g = γ(1 − e^{−λQ})，γ=1e7, λ=6.0(与给定指数型同参数,但**有界** ≤ γ)。"""
    return 1e7 * (1.0 - np.exp(-6.0 * np.asarray(q, float)))


def cand_saturating_exp_p(q):
    return 1e7 * 6.0 * np.exp(-6.0 * np.asarray(q, float))


def cand_hill(q):
    """C2 Hill 型 g = γ Q^λ/(1+Q^λ)，γ=1e7, λ=6.0(有界,中段更陡)。"""
    q = np.asarray(q, float)
    return 1e7 * q ** 6.0 / (1.0 + q ** 6.0)


def cand_hill_p(q):
    q = np.asarray(q, float)
    return 1e7 * 6.0 * q ** 5.0 / (1.0 + q ** 6.0) ** 2


def cand_quadratic(q):
    """C3 二次型 g = γ Q²，γ=4.034287935e9(使 g(1) 与给定指数型的 g(1)=1e7·e^6 相同)。"""
    return 4.034287935e9 * np.asarray(q, float) ** 2


def cand_quadratic_p(q):
    return 2.0 * 4.034287935e9 * np.asarray(q, float)


def run_config(model: Model) -> dict:
    """跑三档锚点 + 主扫描 + 定义 A 二分。"""
    votes = [1e19, 1e22, 1e24]
    anch = []
    for C_b in votes:
        best, _ = model.solve_kkt(C_b)
        if best is None:
            anch.append({"C": C_b, "ok": False})
            continue
        anch.append({"C": C_b, "ok": True, "branch": best["branch"], "N_B": best["N_B"],
                     "D_B": best["D_B"], "Q": best["Q"], "loss": best["loss"],
                     "N_over_D": best["N_over_D"], "cost_shares": best["cost_shares"],
                     "active_set": best["active_set"], "kkt_passed": best["kkt_passed"],
                     "budget_violation_rel": best.get("budget_violation_rel")})
    pts = M.sweep(model, M.SWEEP_MAIN_STEP)
    dA = M.definition_A(model, pts)
    loc = dA["changes"][0]["located_log10_C"] if dA["changes"] else None
    # 成本分项占比排序变化(定义 C)
    dC = M.definition_C(pts)
    return {"anchors": anch,
            "n_sweep_points": len(pts), "sweep_all_kkt_passed": all(p["kkt_passed"] for p in pts),
            "transition_A": {"verdict": dA["verdict"], "location_log10_C": loc,
                             "n_changes": len(dA["changes"])},
            "transition_C": {"verdict": dC["verdict"], "n_changes": dC["n_changes"],
                             "at": [c["at_log10_C"] for c in dC["changes"]]},
            "share_order_at_1e24": pts[-1]["share_order"] if pts else None}


def main() -> None:
    t0 = time.perf_counter()
    law = C.load_law_params()
    res: dict = {"schema_version": 1, "question_id": "Q3", "gate": "G4",
                 "purpose": "兑现裁定 q3_result_verdict=1B 与 q3_stability_verdict=2B 的补算要求",
                 "seed": C.SEED, "law_params": law,
                 "baseline_config": {"Q0": C.Q0_DEFAULT, "L_ctx": L_CTX_DEFAULT,
                                     "form": "exponential"}}

    # ---------- (1) Q0 敏感性
    q0_rows = []
    for q0 in Q0_SCAN:
        md = Model(law, Q0=q0, L_ctx=L_CTX_DEFAULT, form="exponential")
        r = run_config(md)
        a19 = next(a for a in r["anchors"] if a["C"] == 1e19)
        q0_rows.append({"Q0": q0, **r, "Q_star_1e19": a19.get("Q") if a19["ok"] else None})
    qs = [r["Q_star_1e19"] for r in q0_rows if r["Q_star_1e19"] is not None]
    locs = [r["transition_A"]["location_log10_C"] for r in q0_rows
            if r["transition_A"]["location_log10_C"] is not None]
    res["Q0_sensitivity"] = {
        "Q0_scan": Q0_SCAN,
        "source_of_range": "Q1 实测域级 Q 范围 0.223306-0.381496",
        "criterion": ("若跨 Q0 范围的最优 Q* 极差 > 0.10 或转移位置 log10 C 移动 > 0.10，"
                      "则 Q0 是承重参数须显式报敏感性"),
        "rows": q0_rows,
        "Q_star_1e19_range": float(max(qs) - min(qs)) if qs else None,
        "transition_location_range": float(max(locs) - min(locs)) if len(locs) > 1 else None,
        "transition_locations": locs,
        "verdict": ("LOAD_BEARING" if (qs and max(qs) - min(qs) > Q0_CRIT_Q)
                    or (len(locs) > 1 and max(locs) - min(locs) > Q0_CRIT_LOG10C)
                    else "NOT_LOAD_BEARING_IN_TESTED_RANGE"),
    }

    # ---------- (2) 三个候选第四类 g
    cands = [
        ("C1_saturating_exponential", cand_saturating_exp, cand_saturating_exp_p,
         "g = γ(1 − e^(−λQ))，γ=1e7, λ=6.0：与给定指数型同参数但**有界**(≤ γ)，"
         "高 Q 端成本不再爆炸"),
        ("C2_hill", cand_hill, cand_hill_p,
         "g = γQ^λ/(1+Q^λ)，γ=1e7, λ=6.0：有界且中段更陡"),
        ("C3_quadratic", cand_quadratic, cand_quadratic_p,
         "g = γQ²，γ=4.034287935e9(使 g(1) 与指数型 g(1)=1e7·e^6 相同)：多项式族凸改进，避免指数爆炸"),
    ]
    cand_out = {}
    for name, g, gp, desc in cands:
        md = ModelG(law, Q0=C.Q0_DEFAULT, g=g, gp=gp, name=name)
        try:
            cand_out[name] = {"form": desc, "g_at_Q0": float(g(C.Q0_DEFAULT)), "g_at_1": float(g(1.0)),
                              **run_config(md)}
        except Exception as exc:  # noqa: BLE001
            cand_out[name] = {"form": desc, "error": repr(exc)}
    res["fourth_cost_form_candidates"] = {
        "status": "COMPUTED_NOT_CHOSEN — 具体形式属建模判断,须由使用者裁定后采用",
        "reference_given_forms": {k: {"g_coef": v["g_coef"], "g_rate": v["g_rate"]}
                                  for k, v in C.G_SPECS.items()},
        "candidates": cand_out,
    }
    res["elapsed_seconds"] = round(time.perf_counter() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"Q0 scan: Q*_1e19 range = {res['Q0_sensitivity']['Q_star_1e19_range']}")
    print(f"Q0 scan: transition locations = {[round(x,6) for x in locs]}")
    print(f"Q0 scan: transition range = {res['Q0_sensitivity']['transition_location_range']} "
          f"=> {res['Q0_sensitivity']['verdict']}")
    for r in q0_rows:
        a = next(x for x in r["anchors"] if x["C"] == 1e19)
        print(f"  Q0={r['Q0']:.6f}  Q*_1e19={a.get('Q')}  branch={a.get('branch')}  "
              f"trans_A={r['transition_A']['location_log10_C']}")
    for name, d in cand_out.items():
        if "error" in d:
            print(f"  {name}: ERROR {d['error']}")
            continue
        a19 = next(x for x in d["anchors"] if x["C"] == 1e19)
        a24 = next(x for x in d["anchors"] if x["C"] == 1e24)
        print(f"  {name}: Q*_1e19={a19.get('Q')} Q*_1e24={a24.get('Q')} "
              f"trans_A={d['transition_A']['verdict']}@{d['transition_A']['location_log10_C']}")
    print(f"elapsed {res['elapsed_seconds']}s")
    print("WROTE", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
