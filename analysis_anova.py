"""
analysis_anova.py - Kapitola 4: Test rozdílu denní aktivity mezi obdobími.

Postup (přesně v tomto pořadí, jinak se to u obhajoby rozsype):
    1. Vstup: denní počty achievementů, přiřazené do 3 období.
    2. Ověření normality v každém období (Shapiro-Wilk).
    3. Ověření homogenity rozptylů (Levene).
    4. Pokud předpoklady SELHALY → použij Kruskal-Wallis (parametrický
       ekvivalent ANOVY pro neparametrická data) jako primární test.
       ANOVA se počítá jako srovnávací check.
    5. Post-hoc: Tukey HSD (pro ANOVA) + Dunn (pro Kruskal-Wallis).
    6. Effect size: eta² a epsilon² (jen p-value je málo, recenzent
       chce vědět, JAK velký ten rozdíl je).

Hypotézy:
    H0: Průměrná denní aktivita je stejná ve všech třech obdobích.
    H1: Alespoň jedno období má jinou průměrnou denní aktivitu.

Výstup:
    - outputs/anova_results.txt   (lidsky čitelný report)
    - outputs/anova_boxplot.png   (graf pro práci)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

import db
from periods import LABELS, assign_period

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def run() -> None:
    # ----- 1. Načtení dat -------------------------------------------------
    daily = db.load("daily_activity")
    daily["period"] = assign_period(daily["day"])
    daily = daily.dropna(subset=["period"])

    groups = {p: daily.loc[daily["period"] == p, "achievements"].values
              for p in ["pre_covid", "covid", "post_covid"]}

    report: list[str] = []
    add = report.append

    add("=" * 70)
    add("KAPITOLA 4 — TEST VLIVU COVID-19 NA DENNÍ AKTIVITU")
    add("=" * 70)
    add("")
    add("H0: Průměrná denní aktivita je stejná ve všech třech obdobích.")
    add("H1: Alespoň jedno období má jinou průměrnou denní aktivitu.")
    add("Hladina významnosti: α = 0,05")
    add("")

    # ----- 2. Popisná statistika podle období ----------------------------
    add("--- Popisná statistika denní aktivity podle období ---")
    desc = daily.groupby("period")["achievements"].agg(
        ["count", "mean", "median", "std", "min", "max"]
    ).round(1)
    add(desc.to_string())
    add("")

    # ----- 3. Shapiro-Wilk: test normality -------------------------------
    add("--- Shapiro-Wilk test normality (H0: data jsou z normálního rozdělení) ---")
    # Pozn.: Shapiro je spolehlivý do n≈5000. U větších vzorků skoro vždy
    # zamítne i pro prakticky normální data → bereme náhodný sample.
    rng = np.random.default_rng(42)
    normal_ok = True
    for name, vals in groups.items():
        sample = rng.choice(vals, size=min(len(vals), 5000), replace=False)
        W, p = stats.shapiro(sample)
        verdict = "normální" if p > 0.05 else "NENORMÁLNÍ"
        if p <= 0.05:
            normal_ok = False
        add(f"   {LABELS[name]:35s}  W={W:.4f}  p={p:.4g}  → {verdict}")
    add("")

    # ----- 4. Levene: test homogenity rozptylů ---------------------------
    add("--- Levene test homogenity rozptylů (H0: rozptyly jsou stejné) ---")
    levene_W, levene_p = stats.levene(*groups.values(), center="median")
    levene_ok = levene_p > 0.05
    verdict = "stejné" if levene_ok else "RŮZNÉ"
    add(f"   W={levene_W:.4f}  p={levene_p:.4g}  → rozptyly jsou {verdict}")
    add("")

    # ----- 5. Volba primárního testu -------------------------------------
    add("--- Volba primárního testu ---")
    if normal_ok and levene_ok:
        add("   Předpoklady ANOVY splněny → ANOVA je primární test.")
        primary = "anova"
    else:
        add("   Předpoklady ANOVY NEsplněny (sešikmená data, různé rozptyly).")
        add("   → Kruskal-Wallis je primární test, ANOVA je referenční.")
        primary = "kruskal"
    add("")

    # ----- 6. ANOVA ------------------------------------------------------
    add("--- One-way ANOVA ---")
    F, p_anova = stats.f_oneway(*groups.values())
    # eta² = SS_between / SS_total (effect size pro ANOVA)
    all_values = np.concatenate(list(groups.values()))
    grand_mean = all_values.mean()
    ss_total = ((all_values - grand_mean) ** 2).sum()
    ss_between = sum(
        len(g) * (g.mean() - grand_mean) ** 2 for g in groups.values()
    )
    eta_sq = ss_between / ss_total
    add(f"   F = {F:.2f}")
    add(f"   p = {p_anova:.4g}")
    add(f"   η² = {eta_sq:.4f}  (eta-squared, podíl variability vysvětlený obdobím)")
    add(f"   {'ZAMÍTÁME' if p_anova < 0.05 else 'NEZAMÍTÁME'} H0 na hladině 0,05")
    add("")

    # ----- 7. Kruskal-Wallis --------------------------------------------
    add("--- Kruskal-Wallis test (neparametrická alternativa) ---")
    H, p_kruskal = stats.kruskal(*groups.values())
    n = len(all_values)
    k = len(groups)
    epsilon_sq = (H - k + 1) / (n - k)  # effect size pro Kruskal-Wallis
    add(f"   H = {H:.2f}")
    add(f"   p = {p_kruskal:.4g}")
    add(f"   ε² = {epsilon_sq:.4f}")
    add(f"   {'ZAMÍTÁME' if p_kruskal < 0.05 else 'NEZAMÍTÁME'} H0 na hladině 0,05")
    add("")

    # ----- 8. Post-hoc: Tukey HSD ----------------------------------------
    add("--- Tukey HSD post-hoc (které dvojice se liší?) ---")
    tukey = pairwise_tukeyhsd(
        endog=daily["achievements"],
        groups=daily["period"],
        alpha=0.05,
    )
    add(str(tukey))
    add("")

    # ----- 9. Závěr -------------------------------------------------------
    p_primary = p_kruskal if primary == "kruskal" else p_anova
    add("=" * 70)
    add("ZÁVĚR")
    add("=" * 70)
    if p_primary < 0.05:
        add(f"Na hladině významnosti 5 % ZAMÍTÁME H0 (p = {p_primary:.4g}).")
        add("Mezi obdobími existuje statisticky významný rozdíl v průměrné")
        add("denní aktivitě. Konkrétní dvojice viz Tukey HSD výše.")
    else:
        add(f"Na hladině významnosti 5 % NEZAMÍTÁME H0 (p = {p_primary:.4g}).")
        add("Nelze prokázat rozdíl mezi obdobími.")

    # ----- Uložení reportu -----------------------------------------------
    report_text = "\n".join(report)
    print(report_text)

    out = OUTPUT_DIR / "anova_results.txt"
    out.write_text(report_text, encoding="utf-8")
    print(f"\n💾 Report uložen do {out}")

    # ----- Vizualizace ---------------------------------------------------
    _plot_boxplot(daily)


def _plot_boxplot(daily: pd.DataFrame) -> None:
    """Boxplot denní aktivity podle období + překryté průměry."""
    fig, ax = plt.subplots(figsize=(10, 6))
    order = ["pre_covid", "covid", "post_covid"]
    data = [daily.loc[daily["period"] == p, "achievements"].values for p in order]

    bp = ax.boxplot(data, tick_labels=[LABELS[p] for p in order],
                    patch_artist=True, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="red",
                                   markeredgecolor="red", markersize=8))
    for patch, color in zip(bp["boxes"], ["#9ec5e8", "#e89e9e", "#9ee8b8"]):
        patch.set_facecolor(color)

    ax.set_ylabel("Počet odemčených achievementů za den")
    ax.set_title("Distribuce denní aktivity podle období\n"
                 "(červený diamant = průměr, čára = medián)")
    ax.grid(axis="y", alpha=0.3)

    out = OUTPUT_DIR / "anova_boxplot.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"📊 Graf uložen do {out}")


if __name__ == "__main__":
    run()
