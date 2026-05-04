"""
analysis_stl.py - STL dekompozice denní časové řady aktivity.

STL = Seasonal-Trend decomposition using Loess. Rozloží řadu na:
    - Trend     (dlouhodobý směr  odpovídá růstu/poklesu Steamu)
    - Seasonal  (opakující se vzor  roční cyklus s vrcholem v prosinci)
    - Reziduum  (zbytek  anomálie a šum)

"""

from __future__ import annotations

from pathlib import Path

import db
import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.seasonal import STL

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def run() -> None:
    daily = db.load("daily_activity").set_index("day")["achievements"]

    daily = daily.asfreq("D", fill_value=0)
    print("Spouštím STL dekompozici (může chvíli trvat, ~3,6k bodů)...")
    stl = STL(daily, period=365, seasonal=13, robust=True)
    res = stl.fit()

    # ----- Top anomálie podle reziduí ------------------------------------
    resid = res.resid.dropna()
    top_pos = resid.nlargest(10)
    top_neg = resid.nsmallest(5)

    report = [
        "=" * 70,
        "STL DEKOMPOZICE DENNÍ AKTIVITY",
        "=" * 70,
        "",
        "Časové rozpětí: " + f"{daily.index.min().date()} – {daily.index.max().date()}",
        f"Počet dní: {len(daily):,}".replace(",", " "),
        f"Průměr / medián achievementů za den: {daily.mean():.0f} / {daily.median():.0f}",
        "",
        "--- Síla komponent ---",
        f"Variance trendu:    {res.trend.var():,.0f}".replace(",", " "),
        f"Variance sezónnosti:{res.seasonal.var():,.0f}".replace(",", " "),
        f"Variance reziduí:   {res.resid.var():,.0f}".replace(",", " "),
        "",
        "Síla sezónnosti (Hyndman-Athanasopoulos):",
        f"   F_S = max(0, 1 - Var(R) / Var(R+S)) = "
        f"{max(0, 1 - res.resid.var() / (res.resid + res.seasonal).var()):.3f}",
        "Síla trendu:",
        f"   F_T = max(0, 1 - Var(R) / Var(R+T)) = "
        f"{max(0, 1 - res.resid.var() / (res.resid + res.trend).var()):.3f}",
        "",
        "Hodnoty F blízko 1 = silná komponenta; blízko 0 = slabá.",
        "",
        "--- 10 nejvyšších kladných reziduí (anomálně aktivní dny) ---",
    ]
    for date, val in top_pos.items():
        report.append(f"   {date.date()}  reziduum = {val:+,.0f}".replace(",", " "))

    report.append("")
    report.append("--- 5 nejnižších záporných reziduí (anomálně klidné dny) ---")
    for date, val in top_neg.items():
        report.append(f"   {date.date()}  reziduum = {val:+,.0f}".replace(",", " "))

    text = "\n".join(report)
    print(text)
    (OUTPUT_DIR / "stl_results.txt").write_text(text, encoding="utf-8")

    # ----- Graf 4-panel klasika -----------------------------------------
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
    daily.plot(ax=axes[0], color="#444", linewidth=0.5)
    axes[0].set_ylabel("Pozorováno")
    axes[0].set_title("STL dekompozice denní achievement aktivity")

    res.trend.plot(ax=axes[1], color="#1f77b4", linewidth=1.5)
    axes[1].set_ylabel("Trend")

    res.seasonal.plot(ax=axes[2], color="#2ca02c", linewidth=0.7)
    axes[2].set_ylabel("Sezónnost")

    res.resid.plot(ax=axes[3], color="#d62728", linewidth=0.4)
    axes[3].set_ylabel("Reziduum")
    axes[3].set_xlabel("Datum")

    # Vyznačit COVID začátek na trendu pro vizuální argument.
    for ax in axes:
        ax.axvline(
            pd.Timestamp("2020-03-01"),
            color="orange",
            linestyle="--",
            alpha=0.5,
            label="COVID start",
        )
        ax.grid(alpha=0.3)
    axes[1].legend(loc="upper left")

    fig.tight_layout()
    out = OUTPUT_DIR / "stl_decomposition.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\n Graf uložen do {out}")


if __name__ == "__main__":
    run()
