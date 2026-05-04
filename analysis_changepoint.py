"""
analysis_changepoint.py - Detekce bodů změny v časové řadě.

Otázka: Existuje konkrétní datum, kdy se trend aktivity zlomil?
Pokud detekce najde bod blízko březnu 2020 → silný empirický argument
pro vliv COVID-19 (a ne jen popisné srovnání průměrů).

Použité metody:
    1. PELT (Pruned Exact Linear Time) — rychlý, nemusíme předem
       znát počet bodů změny.
    2. Binary segmentation — záložní metoda pro srovnání.

Pracujeme s MĚSÍČNÍMI agregáty, ne s denními. Důvod: denní řada je
zašuměná a algoritmy by detekovaly desítky lokálních fluktuací místo
hlavních zlomů. Měsíční agregát = signal-to-noise lepší o řád.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

try:
    import ruptures as rpt
except ImportError:
    raise SystemExit(
        "Chybí knihovna ruptures. Nainstaluj: pip install ruptures"
    )

import db

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def run() -> None:
    daily = db.load("daily_activity").set_index("day")["achievements"]
    monthly = daily.resample("MS").sum()  # MS = měsíc start

    signal = monthly.values

    # ----- PELT s RBF kostrou (citlivý na změny v rozdělení) -------------
    # pen=10 je heuristika — vyšší = méně bodů změny, nižší = víc.
    # Při 120 měsících (10 let) chceš detekovat ~3-5 bodů, ne 30.
    algo_pelt = rpt.Pelt(model="rbf").fit(signal)
    cps_pelt = algo_pelt.predict(pen=10)

    # ----- Binary segmentation (záložní) ---------------------------------
    # n_bkps=4 → necháme algoritmus najít 4 nejvýraznější body.
    algo_bin = rpt.Binseg(model="l2").fit(signal)
    cps_bin = algo_bin.predict(n_bkps=4)

    def _to_dates(cps: list[int]) -> list[pd.Timestamp]:
        # ruptures vrací indexy včetně koncového (= len(signal)). Odřízneme.
        return [monthly.index[i] for i in cps if i < len(monthly)]

    pelt_dates = _to_dates(cps_pelt)
    bin_dates = _to_dates(cps_bin)

    report = [
        "=" * 70,
        "DETEKCE BODŮ ZMĚNY (CHANGEPOINT DETECTION)",
        "=" * 70,
        "",
        f"Vstup: měsíční agregát achievementů, {len(monthly)} měsíců",
        f"Období: {monthly.index.min().date()} až {monthly.index.max().date()}",
        "",
        "--- PELT s RBF metrikou (penalty=10) ---",
        f"Detekováno {len(pelt_dates)} bodů změny:",
    ]
    for d in pelt_dates:
        report.append(f"   {d.date()}")

    report.append("")
    report.append("--- Binary segmentation (n_breaks=4) ---")
    report.append(f"4 nejvýraznější body změny:")
    for d in bin_dates:
        report.append(f"   {d.date()}")

    report.append("")
    report.append("--- Klíčové události pro srovnání ---")
    report.append("   2020-03-11  WHO vyhlášení pandemie")
    report.append("   2020-03-16  Česko: vyhlášení nouzového stavu")
    report.append("   2021-04-12  Česko: konec nouzového stavu")
    report.append("   2023-09-27  Steam: CS:GO → CS2 přechod")
    report.append("")

    text = "\n".join(report)
    print(text)
    (OUTPUT_DIR / "changepoint.txt").write_text(text, encoding="utf-8")

    # ----- Graf ----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(monthly.index, monthly.values, color="#444", linewidth=1.5,
            label="Měsíční aktivita")

    # PELT body — modré.
    for d in pelt_dates:
        ax.axvline(d, color="#1f77b4", linestyle="-", alpha=0.7, linewidth=1.5)
    # Binseg body — oranžové, čárkovaně.
    for d in bin_dates:
        ax.axvline(d, color="#ff7f0e", linestyle="--", alpha=0.6, linewidth=1.2)

    # Klíčové události — šedé tečkované.
    events = [
        (pd.Timestamp("2020-03-11"), "COVID start"),
        (pd.Timestamp("2023-09-27"), "CS2 release"),
    ]
    for date, label in events:
        ax.axvline(date, color="red", linestyle=":", alpha=0.7)
        ax.text(date, ax.get_ylim()[1] * 0.95, " " + label,
                rotation=90, va="top", fontsize=9, color="red")

    # Custom legenda.
    legend_items = [
        Line2D([0], [0], color="#444", linewidth=1.5, label="Měsíční aktivita"),
        Line2D([0], [0], color="#1f77b4", linewidth=1.5, label="PELT body změny"),
        Line2D([0], [0], color="#ff7f0e", linestyle="--", label="Binseg body změny"),
        Line2D([0], [0], color="red", linestyle=":", label="Klíčové události"),
    ]
    ax.legend(handles=legend_items, loc="upper left")

    ax.set_xlabel("Datum")
    ax.set_ylabel("Achievementy za měsíc")
    ax.set_title("Detekce bodů změny v aktivitě")
    ax.grid(alpha=0.3)

    fig.tight_layout()
    out = OUTPUT_DIR / "changepoint.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\n📊 Graf uložen do {out}")


if __name__ == "__main__":
    run()
