"""
analysis_chi_square.py - Chi-square test rovnoměrnosti dnů v týdnu.

H0: Achievementy jsou rovnoměrně rozděleny přes 7 dní (každý 1/7).
H1: Distribuce není rovnoměrná.

Výstup: outputs/chi_square_dow.txt
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import db

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

DAY_NAMES = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]


def run() -> None:
    daily = db.load("daily_activity")

    daily["dow"] = daily["day"].dt.dayofweek
    observed = daily.groupby("dow")["achievements"].sum().reindex(range(7)).values

    total = observed.sum()
    expected = np.full(7, total / 7)  # uniform null

    chi2, p = stats.chisquare(f_obs=observed, f_exp=expected)

    cramer_v = np.sqrt(chi2 / (total * (7 - 1)))

    table = pd.DataFrame({
        "Den":            DAY_NAMES,
        "Pozorováno":     observed.astype(int),
        "Očekáváno":      expected.round(0).astype(int),
        "Reziduum":       (observed - expected).round(0).astype(int),
        "Std. reziduum":  ((observed - expected) / np.sqrt(expected)).round(2),
    })

    report = [
        "=" * 70,
        "CHI-SQUARE TEST ROVNOMĚRNOSTI DNŮ V TÝDNU (k Tab. 3.1)",
        "=" * 70,
        "",
        "H0: Achievementy jsou rovnoměrně rozděleny přes 7 dní (každý 1/7).",
        "H1: Distribuce není rovnoměrná.",
        "Hladina významnosti: α = 0,05",
        "",
        "--- Tabulka pozorovaných vs. očekávaných četností ---",
        table.to_string(index=False),
        "",
        f"Celkový počet achievementů: {int(total):,}".replace(",", " "),
        "",
        "--- Výsledek testu ---",
        f"   χ² = {chi2:.2f}",
        f"   df = 6  (počet dní − 1)",
        f"   p  = {p:.4g}",
        f"   Cramérovo V = {cramer_v:.4f}  (síla efektu)",
        "",
        f"   {'ZAMÍTÁME' if p < 0.05 else 'NEZAMÍTÁME'} H0 na hladině 0,05",
        "",
        "Interpretace standardizovaných reziduí:",
        "   |z| > 2 → den se významně liší od očekávané rovnoměrné distribuce.",
        "   Kladné z = více aktivity než by odpovídalo rovnoměrnému rozložení,",
        "   záporné z = méně aktivity.",
    ]

    text = "\n".join(report)
    print(text)
    (OUTPUT_DIR / "chi_square_dow.txt").write_text(text, encoding="utf-8")
    print(f"\n💾 Uloženo do {OUTPUT_DIR / 'chi_square_dow.txt'}")


if __name__ == "__main__":
    run()
