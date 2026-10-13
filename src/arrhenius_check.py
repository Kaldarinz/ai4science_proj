"""Независимая проверка E_a другим методом.

Основной расчёт (arrhenius_fit.py) — np.polyfit на ln k от 1/T.
Здесь: явные формулы МНК (ковариация/дисперсия) и метод двух крайних точек.
"""
from pathlib import Path

import numpy as np

R = 8.314462618
RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "rates.csv"
RES = Path(__file__).resolve().parents[1] / "results"
EXCLUDED = {"2024-03"}


def load_series(path: Path) -> tuple[np.ndarray, np.ndarray]:
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
    x = 1.0 / (t_c + 273.15)
    y = np.log(k)

    # Метод 1: явные формулы МНК
    xm, ym = x.mean(), y.mean()
    slope1 = np.sum((x - xm) * (y - ym)) / np.sum((x - xm) ** 2)
    ea1 = -R * slope1

    # Метод 2: две крайние точки (25 °C и 70 °C)
    i_lo, i_hi = int(np.argmin(t_c)), int(np.argmax(t_c))
    slope2 = (y[i_hi] - y[i_lo]) / (x[i_hi] - x[i_lo])
    ea2 = -R * slope2

    ea_ref = 51662.5788  # из основного расчёта, Дж/моль
    dev1 = abs(ea1 - ea_ref) / ea_ref * 100
    dev2 = abs(ea2 - ea_ref) / ea_ref * 100

    RES.mkdir(exist_ok=True)
    out = RES / "arrhenius_check.csv"
    with out.open("w") as f:
        f.write("method,Ea_J_per_mol,Ea_kJ_per_mol,dev_pct_vs_main\n")
        f.write(f"mnk_explicit,{ea1:.6e},{ea1/1000:.4f},{dev1:.4f}\n")
        f.write(f"two_points,{ea2:.6e},{ea2/1000:.4f},{dev2:.4f}\n")

    print(f"MNK explicit: E_a = {ea1/1000:.4f} kJ/mol, dev = {dev1:.4f}%")
    print(f"Two points : E_a = {ea2/1000:.4f} kJ/mol, dev = {dev2:.4f}%")
    print(f"written: {out}")


if __name__ == "__main__":
    main()