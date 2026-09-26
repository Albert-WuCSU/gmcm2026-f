"""Check the idea-document's load-bearing assumptions against the real data.

Two things decide whether its recommendations are usable:
  1. ILR (page 5) needs strictly positive mixture components -> count exact zeros.
  2. The D_eff form (page 8) implies a constant Q-vs-D elasticity ratio -> verify
     symbolically and numerically, because that governs identifiability.
"""
import csv
from pathlib import Path

ROOT = Path('workspace/data_raw/real_attachments/A_data_value/regmix_tables')
MIX = ['train_mixture_1m.csv', 'test_mixture_1m.csv', 'test_mixture_60m.csv',
       'test_mixture_1B.csv', 'est_mixture_10b.csv', 'est_mixture_70b.csv']


def zero_audit():
    print('=== ILR feasibility: exact zeros in mixture tables ===')
    for name in MIX:
        with (ROOT / name).open(encoding='utf-8-sig', newline='') as fh:
            rows = list(csv.DictReader(fh))
        cols = [c for c in rows[0] if c.startswith('train_the_pile_')]
        vals = [[float(r[c]) for c in cols] for r in rows]
        n_zero = sum(1 for row in vals for v in row if v == 0.0)
        n_tiny = sum(1 for row in vals for v in row if 0.0 < v < 1e-6)
        rowsums = [sum(row) for row in vals]
        rows_with_zero = sum(1 for row in vals if any(v == 0.0 for v in row))
        gmin = min(v for row in vals for v in row)
        print(f'{name:26s} rows={len(rows):4d} zeros={n_zero:5d} '
              f'rows_with_zero={rows_with_zero:4d}/{len(rows)} tiny(<1e-6)={n_tiny:4d} '
              f'min={gmin:.3e} rowsum∈[{min(rowsums):.6f},{max(rowsums):.6f}]')


def elasticity_algebra():
    """D_eff = D*Q^g*exp(b'z);  L = E + A*N^-a + B*D_eff^-beta.

    dL/dQ = -beta*g/Q * B*D_eff^-beta
    dL/dD = -beta/D   * B*D_eff^-beta
    => (dL/dQ * Q) / (dL/dD * D) = g   for all N, D, Q.
    """
    print()
    print('=== D_eff form: Q-vs-D elasticity ratio ===')
    E, A, a, B, beta, g = 1.8, 400.0, 0.34, 300.0, 0.28, 2.0
    b_dot_z = 0.0
    h = 1e-7
    import math

    def L(N, D, Q):
        Deff = D * (Q ** g) * math.exp(b_dot_z)
        return E + A * N ** (-a) + B * Deff ** (-beta)

    print(f'{"N":>10s} {"D":>10s} {"Q":>5s} {"eps_Q":>10s} {"eps_D":>10s} {"ratio":>8s}')
    for N in (1e8, 1e10):
        for D in (1e9, 1e11):
            for Q in (0.4, 0.8):
                L0 = L(N, D, Q)
                eQ = (L(N, D, Q + h) - L0) / h * Q / L0
                eD = (L(N, D + h * D, Q) - L0) / (h * D) * D / L0
                print(f'{N:10.1e} {D:10.1e} {Q:5.2f} {eQ:10.5f} {eD:10.5f} {eQ/eD:8.4f}')
    print(f'gamma set to {g} -> ratio is constant and equals gamma exactly.')
    print('Consequence: along the Q direction the data only identifies the product')
    print('beta*gamma; beta must be pinned down by real N-D data (B1) first.')


if __name__ == '__main__':
    zero_audit()
    elasticity_algebra()
