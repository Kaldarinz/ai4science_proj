"""График ln k от 1/T по сериям 2024-01, 2024-02, 2024-04.

Серия 2024-03 исключена (неисправный термостат). Прямая — МНК-регрессия
из arrhenius_fit.py. Сохраняет PNG в results/.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "rates.csv"
RES = Path(__file__).resolve().parents[1] / "results"
EXCLUDED = {"2024-03"}


def load_series(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Возвращает (T_C, k, series) для всех серий, кроме исключённых."""
    t_c, k, series = [], [], []
    with path.open() as f:
        next(f)
        for line in f:
            s, tc, ks = line.strip().split(",")
            if s in EXCLUDED:
                continue
            t_c.append(float(tc))
            k.append(float(ks))
            series.append(s)
    return np.array(t_c), np.array(k), series


def main() -> None:
    t_c, k, series = load_series(RAW)
    x = 1.0 / (t_c + 273.15)
    y = np.log(k)

    slope, intercept = np.polyfit(x, y, 1)
    x_fit = np.linspace(x.min(), x.max(), 100)
    y_fit = slope * x_fit + intercept

    fig, ax = plt.subplots(figsize=(7, 5))
    for s in sorted(set(series)):
        mask = np.array(series) == s
        ax.scatter(x[mask], y[mask], label=f"Серия {s}", s=40)
    ax.plot(x_fit, y_fit, "k--", lw=1.2,
            label=f"МНК: ln k = {slope:.3f}/T + {intercept:.3f}")

    ax.set_xlabel("1/T, K$^{-1}$")
    ax.set_ylabel("ln k, k в с$^{-1}$")
    ax.set_title("Закон Аррениуса: ln k от 1/T (25–70 °C)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    RES.mkdir(exist_ok=True)
    out = RES / "arrhenius_plot.png"
    fig.savefig(out, dpi=150)
    print(f"written: {out}")


if __name__ == "__main__":
    main()