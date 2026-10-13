"""Закон Аррениуса: ln k = ln A - E_a/(R T).

Основной расчёт: МНК-регрессия ln k от 1/T по сериям 2024-01, 2024-02, 2024-04.
Серия 2024-03 исключена (неисправный термостат).
"""
from pathlib import Path

import numpy as np

R = 8.314462618  # Дж/(моль·К)

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "rates.csv"
RES = Path(__file__).resolve().parents[1] / "results"
EXCLUDED = {"2024-03"}


def load_series(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Возвращает (T_C, k) для всех серий, кроме исключённых."""
    t_c, k = [], []
    with path.open() as f:
        next(f)
        for line in f:
            series, tc, ks = line.strip().split(",")
            if series in EXCLUDED:
                continue
            t_c.append(float(tc))
            k.append(float(ks))
    return np.array(t_c), np.array(k)


def main() -> None:
    t_c, k = load_series(RAW)
    t_k = t_c + 273.15
    x = 1.0 / t_k
    y = np.log(k)

    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot

    ea = -R * slope  # Дж/моль

    RES.mkdir(exist_ok=True)
    out = RES / "arrhenius_fit.csv"
    with out.open("w") as f:
        f.write("n,slope_1_over_K,intercept,R2,Ea_J_per_mol,Ea_kJ_per_mol\n")
        f.write(f"{len(x)},{slope:.6e},{intercept:.6e},{r2:.6f},{ea:.6e},{ea/1000:.4f}\n")

    print(f"n = {len(x)}")
    print(f"slope = {slope:.6e} 1/K")
    print(f"intercept = {intercept:.6e}")
    print(f"R^2 = {r2:.6f}")
    print(f"E_a = {ea:.4f} J/mol = {ea/1000:.4f} kJ/mol")
    print(f"written: {out}")


if __name__ == "__main__":
    main()