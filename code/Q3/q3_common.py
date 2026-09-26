"""Q3 公共模块:目标函数、三类成本函数、分段 KKT 求解、数值对照。

依 code/Q3/q3_code_plan.md。批准决策:methods/Q3/q3_decisions.jsonl 三条
  q3_p_joint_optimization            = B_main_plus_C_supplement  ⇒ z_p=0,决策变量 (N,D,Q)
  q3_structural_transition_definition= A_main_plus_D_reported_as_contrast
  q3_optimum_acceptability_criterion = C  ⇒ KKT 硬判据,Chinchilla 仅参考

单位约定(GC10):N_B, D_B 以十亿为单位;成本式中 N = N_B*1e9, D = D_B*1e9。
命名:成本函数参数记 g_coef / g_rate,**不复用**标度律的 gamma(计划 §2 命名冲突警告)。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq, minimize

ROOT = Path(__file__).resolve().parents[2]
SEED = 20260924
ETA = 2e-4
L_CTX_FEASIBLE = [2048, 4096, 8192, 32768, 131072]      # C7 实测可行取值
L_CTX_CRIT = 6.0 / ETA                                   # = 30000,题目给定闭式
L_CTX_DEFAULT = 2048
BUDGET_ANCHORS = [1e19, 1e22, 1e24]
R_CHINCHILLA = 20.0          # Hoffmann et al. 2022 Approach 1/2 的 ~20 tokens/param
Q0_DEFAULT = 0.35            # 未经使用者裁定,须写入 run_summary.Q0_spec

# 三类 g(Q):题目附件 B 给定
G_SPECS = {
    "exponential":    {"g_coef": 1e7, "g_rate": 6.0},
    "power":          {"g_coef": 5e9, "g_rate": 4.0},
    "log_asymptotic": {"g_coef": 2e9, "g_rate": 10.0},
}


def g_value(q, form):
    c, r = G_SPECS[form]["g_coef"], G_SPECS[form]["g_rate"]
    if form == "exponential":
        return c * np.exp(r * q)
    if form == "power":
        return c * q ** r
    return c * np.log1p(r * q)


def g_prime(q, form):
    c, r = G_SPECS[form]["g_coef"], G_SPECS[form]["g_rate"]
    if form == "exponential":
        return c * r * np.exp(r * q)
    if form == "power":
        return c * r * q ** (r - 1.0)
    return c * r / (1.0 + r * q)


def load_law_params():
    """取 Q2 已过 G3 的 B1 侧参数(真实数据支撑)。不读原始数据。"""
    src = ROOT / "results/Q2/experiments/round1/metrics/q2_M1s.json"
    p = json.loads(src.read_text(encoding="utf-8"))["stage3_joint_wls"]["M1s_params"]
    return {"E": p["E_B1"], "A": p["A_B1"], "alpha": p["alpha_B1"],
            "B": p["B_B1"], "beta": p["beta"], "gamma": p["gamma"],
            "source": str(src.relative_to(ROOT)).replace("\\", "/")}


class Model:
    """目标函数、成本式与分段 KKT。z_p=0(裁定1=B) ⇒ exp(b^T z_p)=1 已消去。"""

    def __init__(self, law, Q0=Q0_DEFAULT, L_ctx=L_CTX_DEFAULT, form="exponential"):
        self.E, self.A, self.al = law["E"], law["A"], law["alpha"]
        self.B, self.be, self.ga = law["B"], law["beta"], law["gamma"]
        self.Q0, self.L_ctx, self.form = Q0, L_ctx, form
        self.k = 6.0 + ETA * L_ctx          # 与 N*D 成正比的成本合并系数

    # ---- 目标与成本 ----
    def loss(self, N_B, D_B, Q):
        return self.E + self.A * N_B ** (-self.al) + self.B * (D_B * Q ** self.ga) ** (-self.be)

    def dg(self, Q):
        return max(g_value(Q, self.form) - g_value(self.Q0, self.form), 0.0)

    def cost_parts(self, N_B, D_B, Q):
        N, D = N_B * 1e9, D_B * 1e9
        return {"C_train": 6.0 * N * D,
                "C_Q": D * self.dg(Q),
                "C_attn": ETA * N * D * self.L_ctx}

    def cost(self, N_B, D_B, Q):
        return sum(self.cost_parts(N_B, D_B, Q).values())

    # ---- KKT 约减式(计划 §4.1)----
    def R1(self, N_B, D_B, Q):
        """α·A·N^-α·(k·N + Δg) − β·B·S^-β·k·N = 0,单位:N,Δg 均为 FLOPs/token 量纲。"""
        S = D_B * Q ** self.ga
        kN = self.k * N_B * 1e9
        lhs = self.al * self.A * N_B ** (-self.al) * (kN + self.dg(Q))
        rhs = self.be * self.B * S ** (-self.be) * kN
        return lhs - rhs

    def R2(self, N_B, Q):
        """γ·(k·N + Δg) − Q·g'(Q) = 0。λ 与 D 全消,故只含 (N,Q)。"""
        return self.ga * (self.k * N_B * 1e9 + self.dg(Q)) - Q * g_prime(Q, self.form)

    def N_from_R2(self, Q):
        """由 R2 显式解 N_B(仅内点段可用)。返回 None 表示该 Q 下 N ≤ 0,不可行。"""
        v = Q * g_prime(Q, self.form) / self.ga - self.dg(Q)
        return v / (self.k * 1e9) if v > 0 else None

    def D_from_budget(self, N_B, Q, C):
        den = self.k * N_B * 1e18 + 1e9 * self.dg(Q)
        return C / den if den > 0 else None

    # ---- 乘子 ----
    def multipliers(self, N_B, D_B, Q):
        """λ(预算)、μ(Q≤1 的乘子)、nu(Q≥Q0 的乘子)。"""
        S = D_B * Q ** self.ga
        lam = (self.al * self.A * N_B ** (-self.al - 1.0)) / (self.k * D_B * 1e18)
        dQ_benefit = self.be * self.ga * self.B * S ** (-self.be) / Q
        dQ_cost = lam * D_B * 1e9 * g_prime(Q, self.form)
        return {"lambda": float(lam),
                "mu_upper": float(dQ_benefit - dQ_cost),    # Q=1 段须 ≥ 0
                "nu_lower": float(dQ_cost - dQ_benefit)}    # Q=Q0 段须 ≥ 0

    # ---- 三个分支(计划 §4.1,必须全部枚举)----
    def _pack(self, N_B, D_B, Q, branch, C):
        if N_B is None or D_B is None or N_B <= 0 or D_B <= 0:
            return None
        parts = self.cost_parts(N_B, D_B, Q)
        tot = sum(parts.values())
        m = self.multipliers(N_B, D_B, Q)
        return {"branch": branch, "N_B": float(N_B), "D_B": float(D_B), "Q": float(Q),
                "loss": float(self.loss(N_B, D_B, Q)),
                "cost_total": float(tot),
                "cost_parts": {k: float(v) for k, v in parts.items()},
                "cost_shares": {k: float(v / tot) for k, v in parts.items()},
                "budget_violation_rel": float((tot - C) / C),
                "N_over_D": float(N_B / D_B), "D_over_N": float(D_B / N_B),
                "multipliers": m,
                "R1_residual_rel": self._r1_rel(N_B, D_B, Q),
                "R2_residual_rel": self._r2_rel(N_B, Q, branch)}

    def _r1_rel(self, N_B, D_B, Q):
        S = D_B * Q ** self.ga
        kN = self.k * N_B * 1e9
        a = self.al * self.A * N_B ** (-self.al) * (kN + self.dg(Q))
        b = self.be * self.B * S ** (-self.be) * kN
        scale = max(abs(a), abs(b), 1e-300)
        return float(abs(a - b) / scale)

    def _r2_rel(self, N_B, Q, branch):
        if branch != "interior":
            return None            # R2 只在内点段成立(边界段由 μ/nu 取代)
        a = self.ga * (self.k * N_B * 1e9 + self.dg(Q))
        b = Q * g_prime(Q, self.form)
        return float(abs(a - b) / max(abs(a), abs(b), 1e-300))

    def branch_interior(self, C, n_grid=400):
        """分支 I:Q0 < Q < 1。R2 给 N(Q),预算给 D(Q),R1 成为 Q 的单变量方程。"""
        def F(Q):
            N_B = self.N_from_R2(Q)
            if N_B is None:
                return np.nan
            D_B = self.D_from_budget(N_B, Q, C)
            if D_B is None or D_B <= 0:
                return np.nan
            return self.R1(N_B, D_B, Q)

        lo, hi = self.Q0 + 1e-9, 1.0 - 1e-12
        qs = np.linspace(lo, hi, n_grid)
        vals = np.array([F(q) for q in qs])
        out = []
        for i in range(len(qs) - 1):
            a, b = vals[i], vals[i + 1]
            if np.isnan(a) or np.isnan(b) or a == 0.0 or a * b > 0:
                continue
            try:
                q = brentq(F, qs[i], qs[i + 1], xtol=1e-14, rtol=1e-15, maxiter=300)
            except Exception:
                continue
            N_B = self.N_from_R2(q)
            r = self._pack(N_B, self.D_from_budget(N_B, q, C), q, "interior", C)
            if r:
                out.append(r)
        return out

    def _solve_fixed_Q(self, C, Q, branch, n_grid=600):
        """分支 II/III:Q 固定,预算给 D(N),R1 成为 N 的单变量方程。"""
        def F(N_B):
            D_B = self.D_from_budget(N_B, Q, C)
            if D_B is None or D_B <= 0:
                return np.nan
            return self.R1(N_B, D_B, Q)

        ns = np.logspace(-6, 4, n_grid)
        vals = np.array([F(n) for n in ns])
        out = []
        for i in range(len(ns) - 1):
            a, b = vals[i], vals[i + 1]
            if np.isnan(a) or np.isnan(b) or a == 0.0 or a * b > 0:
                continue
            try:
                n = brentq(F, ns[i], ns[i + 1], xtol=1e-14, rtol=1e-15, maxiter=300)
            except Exception:
                continue
            r = self._pack(n, self.D_from_budget(n, Q, C), Q, branch, C)
            if r:
                out.append(r)
        return out

    def branch_upper(self, C):
        return self._solve_fixed_Q(C, 1.0, "upper_Q_eq_1")

    def branch_lower(self, C):
        return self._solve_fixed_Q(C, self.Q0, "lower_Q_eq_Q0")

    # ---- KKT 硬判据与分支选择(计划 §4.2,裁定3=C)----
    # 预声明阈值,不事后放宽
    TOL_FEAS = 1e-9          # 预算可行性
    TOL_STAT = 1e-8          # 驻点残差(相对)
    TOL_MULT = 1e-8          # 乘子符号容差

    def kkt_audit(self, r, C):
        """五项硬判据。返回 (全过?, 逐项结果)。"""
        b, m = r["branch"], r["multipliers"]
        checks = {
            "budget_feasible": r["budget_violation_rel"] <= self.TOL_FEAS,
            "stationarity_R1": r["R1_residual_rel"] < self.TOL_STAT,
            "stationarity_R2": (r["R2_residual_rel"] < self.TOL_STAT
                                if b == "interior" else None),
            "complementary_slackness": None,
            "lambda_positive": m["lambda"] > 0.0,
            "bounds_ok": (self.Q0 - 1e-12 <= r["Q"] <= 1.0 + 1e-12
                          and r["N_B"] > 0 and r["D_B"] > 0),
        }
        # 互补松弛:预算紧(已由构造保证等式),Q 侧按分支判乘子符号
        if b == "interior":
            # 内点 ⇒ Q 的两个界都非活跃 ⇒ mu 与 nu 均须为 0。
            # 该项同时交叉验证 lambda(由 ∂N 得)与 R2(由 ∂Q÷∂D 得)的一致性。
            denom = max(abs(m["mu_upper"]), abs(m["nu_lower"]),
                        self.be * self.ga * self.B, 1e-300)
            checks["complementary_slackness"] = abs(m["mu_upper"]) / denom < 1e-6
        elif b == "upper_Q_eq_1":
            checks["complementary_slackness"] = m["mu_upper"] >= -self.TOL_MULT
        else:
            checks["complementary_slackness"] = m["nu_lower"] >= -self.TOL_MULT
        passed = all(v for v in checks.values() if v is not None)
        return passed, checks

    def active_set(self, r):
        """活跃约束集(裁定2=A 的主定义所依赖的对象)。预算恒活跃。"""
        s = ["budget"]
        if r["branch"] == "upper_Q_eq_1":
            s.append("Q_le_1")
        elif r["branch"] == "lower_Q_eq_Q0":
            s.append("Q_ge_Q0")
        return s

    def solve_kkt(self, C):
        """三分支全枚举 → 丢弃不可行/乘子符号错 → 取 Loss 最小。"""
        cands = self.branch_interior(C) + self.branch_upper(C) + self.branch_lower(C)
        for r in cands:
            ok, checks = self.kkt_audit(r, C)
            r["kkt_passed"], r["kkt_checks"] = ok, checks
            r["active_set"] = self.active_set(r)
        valid = [r for r in cands if r["kkt_passed"]]
        pool, degraded = (valid, False) if valid else (
            [r for r in cands if r["budget_violation_rel"] <= 1e-6], True)
        if not pool:
            return None, cands
        best = min(pool, key=lambda r: r["loss"])
        best["selected_from_degraded_pool"] = degraded
        best["n_branch_candidates"] = len(cands)
        return best, cands

    def solve_numeric(self, C, n_start=8):
        """多起点 SLSQP。**仅用于 fallback 触发判定**,不作结果报出(计划 §12)。"""
        def obj(x):
            return self.loss(10 ** x[0], 10 ** x[1], x[2])

        def con(x):
            return (C - self.cost(10 ** x[0], 10 ** x[1], x[2])) / C

        rng = np.random.default_rng(SEED)
        base = 0.5 * np.log10(max(C / 6.0 / 1e18, 1e-12))
        best = None
        for _ in range(n_start):
            x0 = np.array([base + rng.uniform(-1, 1), base + rng.uniform(-1, 1),
                           rng.uniform(self.Q0 + 0.01, 0.99)])
            try:
                res = minimize(obj, x0, method="SLSQP",
                               bounds=[(-4, 5), (-4, 6), (self.Q0, 1.0)],
                               constraints=[{"type": "ineq", "fun": con}],
                               options={"maxiter": 500, "ftol": 1e-12})
            except Exception:
                continue
            if not res.success or con(res.x) < -1e-6:
                continue
            if best is None or res.fun < best.fun:
                best = res
        if best is None:
            return None
        N_B, D_B, Q = 10 ** best.x[0], 10 ** best.x[1], best.x[2]
        act = ["budget"]
        if Q >= 1.0 - 1e-6:
            act.append("Q_le_1")
        elif Q <= self.Q0 + 1e-6:
            act.append("Q_ge_Q0")
        return {"N_B": float(N_B), "D_B": float(D_B), "Q": float(Q),
                "loss": float(best.fun), "active_set": act,
                "budget_violation_rel": float((self.cost(N_B, D_B, Q) - C) / C)}
