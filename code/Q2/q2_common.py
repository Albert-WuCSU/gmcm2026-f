"""Q2 共享层：数据加载、多起点拟合、来源分层 WLS、自助。

计划见 code/Q2/q2_code_plan.md。6 条裁定见 methods/Q2/q2_decisions.jsonl。

自助分组的事实依据（本文件实测，非假设）：
  B1 的 run_id 每行唯一（1176 个）⇒ 按 run_id 分组 == 逐行重抽样，是空操作。
  B1 的真实相关结构是 N（仅 8 个取值），同一 N 内为一条训练轨迹（D 递增）、行间强相关
  ⇒ B1 自助按 N 分组（8 组，区间偏宽但诚实）；同时报逐行版作对照。
  B7 为 9(N)x5(D)x10(Q) 独立设计点 ⇒ 逐行重抽样合适。
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "workspace/data_raw/real_attachments"
BDIR = RAW / "B_scaling_laws"
Q1TAB = ROOT / "results/Q1/experiments/round1/tables"

SEED = 20260924

PATHS = {
    "B1": BDIR / "pythia_training_log_existing.csv",
    "B2": BDIR / "cerebras_training_log.csv",
    "B4": BDIR / "scaling_baseline.csv",
    "B5": BDIR / "published_scaling_data.csv",
    "B7": BDIR / "supplementary_NQ_experiment_expanded.csv",
}


def _read(p: Path) -> list[dict]:
    return list(csv.DictReader(p.open(encoding="utf-8-sig")))


def load_nd(code: str) -> dict:
    """加载 (N, D, L) 三元组。B1/B2 另带 N 分组键。"""
    rows = _read(PATHS[code])
    N = np.array([float(r["N_params_B"]) for r in rows])
    D = np.array([float(r["D_tokens_B"]) for r in rows])
    L = np.array([float(r["val_loss"]) for r in rows])
    ok = np.isfinite(N) & np.isfinite(D) & np.isfinite(L) & (N > 0) & (D > 0)
    out = {"N": N[ok], "D": D[ok], "L": L[ok], "n": int(ok.sum()),
           "n_dropped": int((~ok).sum()), "source": code}
    out["group"] = out["N"].copy()          # B1/B2 的轨迹分组键
    return out


def load_b7() -> dict:
    rows = _read(PATHS["B7"])
    N = np.array([float(r["N_params_B"]) for r in rows])
    D = np.array([float(r["D_tokens_B"]) for r in rows])
    Q = np.array([float(r["Q_score"]) for r in rows])
    L = np.array([float(r["val_loss"]) for r in rows])
    ok = np.isfinite(N) & np.isfinite(D) & np.isfinite(L) & np.isfinite(Q) & (N > 0) & (D > 0) & (Q > 0)
    return {"N": N[ok], "D": D[ok], "Q": Q[ok], "L": L[ok], "n": int(ok.sum()),
            "n_dropped": int((~ok).sum()), "source": "B7",
            "Q_levels": sorted(set(Q[ok].tolist()))}


def load_q1_w() -> tuple[np.ndarray, list[str]]:
    """Q1c 的 M0c 17 维系数 w（域级 Loss 水平）。p 与 Q 只经 Q1 输出引入，不读附件 A 原始文件。"""
    rows = [r for r in _read(Q1TAB / "q1c_coefficients.csv") if r["method"] == "M0c"]
    cols = [r["feature"] for r in rows]
    w = np.array([float(r["coef"]) for r in rows])
    return w, cols


def load_q1_domain_Q() -> dict[str, float]:
    """Q1 的域级 Q（M1, pooled, huber 聚合）。"""
    out = {}
    for r in _read(Q1TAB / "q1a_domain_quality.csv"):
        if r["method"] == "M1" and r["population"] == "pooled":
            out[r["domain"]] = float(r["huber"])
    return out


# ------------------------------------------------------------------ 拟合
def _multistart(resid, lo, hi, n_start=12, seed=SEED, max_nfev=20000):
    rng = np.random.default_rng(seed)
    best = None
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    for _ in range(n_start):
        x0 = lo + (hi - lo) * rng.uniform(0.02, 0.5, size=len(lo))
        try:
            r = least_squares(resid, x0, bounds=(lo, hi), max_nfev=max_nfev)
        except Exception:
            continue
        if best is None or r.cost < best.cost:
            best = r
    if best is None:
        raise RuntimeError("all starts failed")
    return best


def fit_classic(N, D, L, seed=SEED):
    """M0s: L = E + A*N^-alpha + B*D^-beta"""
    def resid(th):
        E, A, a, Bc, b = th
        return E + A * N ** (-a) + Bc * D ** (-b) - L
    r = _multistart(resid, [0, 0, 1e-4, 0, 1e-4], [5, 50, 2, 50, 2], seed=seed)
    p = dict(zip(["E", "A", "alpha", "B", "beta"], map(float, r.x)))
    p["rmse"] = float(np.sqrt(np.mean(r.fun ** 2)))
    return p


def predict_classic(p, N, D):
    return p["E"] + p["A"] * N ** (-p["alpha"]) + p["B"] * D ** (-p["beta"])


def fit_gamma_on_b7(N, D, Q, L, beta_fixed, seed=SEED):
    """M1s 阶段 2：beta 固定（由 B1 钉住），估 gamma 与 B7 专属 E/A/alpha/B。

    L = E_B7 + A'*N^-alpha' + B'*(D*Q^gamma)^-beta
    z_p = 0（B7 无配比列）⇒ exp(b^T z_p) = 1，该因子不参与本阶段。
    """
    def resid(th):
        E, A, a, Bc, g = th
        return E + A * N ** (-a) + Bc * (D * Q ** g) ** (-beta_fixed) - L
    r = _multistart(resid, [0, 0, 1e-4, 0, 1e-4], [5, 50, 2, 50, 10], seed=seed)
    p = dict(zip(["E_B7", "A", "alpha", "B", "gamma"], map(float, r.x)))
    p["beta_fixed"] = float(beta_fixed)
    p["rmse"] = float(np.sqrt(np.mean(r.fun ** 2)))
    return p


def predict_m1s(p, N, D, Q, E_key="E_B7"):
    return (p[E_key] + p["A"] * N ** (-p["alpha"])
            + p["B"] * (D * Q ** p["gamma"]) ** (-p["beta_fixed"]))


# --------------------------------------------------- 来源分层 WLS（裁定 3=B）
def fit_joint_wls(b1, b7, sigma_b1, sigma_b7, with_Q: bool, seed=SEED):
    """联合拟合，来源专属 E_s（P1），形状参数共享。

    with_Q=True  -> M1s_joint: 参数 (E_B1, E_B7, A, alpha, B, beta, gamma)
    with_Q=False -> M0s_joint: 参数 (E_B1, E_B7, A, alpha, B, beta)，无 Q 通道
                   （B7 上加自有截距，使与 M1s 成嵌套比较、仅差 gamma 一个参数；
                    这是 P1『E 跨源不可共享』的机械后果，不是建模选择）
    B1 上 Q 恒为 1（无 Q 变化）⇒ Q^gamma = 1，gamma 不受 B1 约束。
    """
    n1, n7 = b1["n"], b7["n"]
    w1, w7 = 1.0 / sigma_b1 ** 2, 1.0 / sigma_b7 ** 2

    def resid(th):
        if with_Q:
            E1, E7, A, a, Bc, b, g = th
        else:
            E1, E7, A, a, Bc, b = th
            g = 0.0
        r1 = E1 + A * b1["N"] ** (-a) + Bc * b1["D"] ** (-b) - b1["L"]
        Deff7 = b7["D"] * (b7["Q"] ** g if with_Q else 1.0)
        r7 = E7 + A * b7["N"] ** (-a) + Bc * Deff7 ** (-b) - b7["L"]
        return np.concatenate([r1 * np.sqrt(w1), r7 * np.sqrt(w7)])

    lo = [0, 0, 0, 1e-4, 0, 1e-4] + ([1e-4] if with_Q else [])
    hi = [5, 5, 50, 2, 50, 2] + ([10] if with_Q else [])
    r = _multistart(resid, lo, hi, seed=seed)
    keys = ["E_B1", "E_B7", "A", "alpha", "B", "beta"] + (["gamma"] if with_Q else [])
    p = dict(zip(keys, map(float, r.x)))
    if not with_Q:
        p["gamma"] = 0.0
    p["beta_fixed"] = p["beta"]
    # 分源未加权 RMSE（可比口径）
    p["rmse_B1"] = float(np.sqrt(np.mean((
        p["E_B1"] + p["A"] * b1["N"] ** (-p["alpha"]) + p["B"] * b1["D"] ** (-p["beta"]) - b1["L"]) ** 2)))
    Deff7 = b7["D"] * (b7["Q"] ** p["gamma"] if with_Q else 1.0)
    p["rmse_B7"] = float(np.sqrt(np.mean((
        p["E_B7"] + p["A"] * b7["N"] ** (-p["alpha"]) + p["B"] * Deff7 ** (-p["beta"]) - b7["L"]) ** 2)))
    p["n_B1"], p["n_B7"] = n1, n7
    return p


# ------------------------------------------------------------------ 自助
def fit_joint_wls_source_shape(b1, b7, sigma_b1, sigma_b7, with_Q: bool, seed=SEED, n_start=12):
    """联合 WLS，**来源专属** E_s/A_s/alpha_s/B_s，仅 beta 与 gamma 共享。

    依据 P8（workspace/data/q2_probe_shape_sharing.json）：强制共享 A/alpha/B 造成的 gamma
    位移达其自助区间宽度的 98.5%，判 FAIL ⇒ 形状参数须来源专属。

    结构后果（须如实报告）：B1 上 Q=1 ⇒ gamma 只受 B7 约束；beta 因 B1 权重压倒性优势
    而实质由 B1 决定。故本式在数值上等价于「B1 定 beta、B7 定 gamma」的两段式，
    裁定3=B 的 WLS 加权机制仍被忠实实现，只是在该参数结构下无实质作用。
    """
    w1, w7 = 1.0 / sigma_b1 ** 2, 1.0 / sigma_b7 ** 2

    def resid(th):
        E1, A1, a1, B1c, E7, A7, a7, B7c, b = th[:9]
        g = th[9] if with_Q else 0.0
        r1 = E1 + A1 * b1["N"] ** (-a1) + B1c * b1["D"] ** (-b) - b1["L"]
        Deff7 = b7["D"] * (b7["Q"] ** g if with_Q else 1.0)
        r7 = E7 + A7 * b7["N"] ** (-a7) + B7c * Deff7 ** (-b) - b7["L"]
        return np.concatenate([r1 * np.sqrt(w1), r7 * np.sqrt(w7)])

    lo = [0, 0, 1e-4, 0, 0, 0, 1e-4, 0, 1e-4] + ([1e-4] if with_Q else [])
    hi = [5, 50, 2, 50, 5, 50, 2, 50, 2] + ([10] if with_Q else [])
    r = _multistart(resid, lo, hi, seed=seed, n_start=n_start)
    keys = ["E_B1", "A_B1", "alpha_B1", "B_B1", "E_B7", "A_B7", "alpha_B7", "B_B7", "beta"]
    keys += ["gamma"] if with_Q else []
    p = dict(zip(keys, map(float, r.x)))
    if not with_Q:
        p["gamma"] = 0.0
    p["beta_fixed"] = p["beta"]
    p["rmse_B1"] = float(np.sqrt(np.mean((
        p["E_B1"] + p["A_B1"] * b1["N"] ** (-p["alpha_B1"])
        + p["B_B1"] * b1["D"] ** (-p["beta"]) - b1["L"]) ** 2)))
    Deff7 = b7["D"] * (b7["Q"] ** p["gamma"] if with_Q else 1.0)
    p["rmse_B7"] = float(np.sqrt(np.mean((
        p["E_B7"] + p["A_B7"] * b7["N"] ** (-p["alpha_B7"])
        + p["B_B7"] * Deff7 ** (-p["beta"]) - b7["L"]) ** 2)))
    p["n_B1"], p["n_B7"] = b1["n"], b7["n"]
    return p


def boot_indices(group: np.ndarray, rng, mode: str) -> np.ndarray:
    """mode='grouped' 按 group 键整组重抽；mode='row' 逐行重抽。"""
    if mode == "row":
        return rng.integers(0, len(group), len(group))
    keys = np.unique(group)
    picked = rng.choice(keys, size=len(keys), replace=True)
    idx = []
    for k in picked:
        idx.append(np.flatnonzero(group == k))
    return np.concatenate(idx)


def ci95(v: np.ndarray) -> list[float]:
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if v.size == 0:
        return [float("nan"), float("nan")]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
