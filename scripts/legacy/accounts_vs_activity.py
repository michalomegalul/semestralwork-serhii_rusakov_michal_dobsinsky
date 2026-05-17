"""
Srovnání trendů: nové účty vs achievement aktivita.
Statistické testování COVID efektu na obou metrikách.

Použití:
    source ~/steam_env/bin/activate
    pip install psycopg2-binary matplotlib pandas numpy statsmodels scipy
    python3 accounts_vs_activity.py

Výstupy:
    accounts_vs_activity.png  - Dual-axis graf: nové účty vs aktivita
    accounts_stl.png          - STL dekompozice nových účtů
    accounts_stats.txt        - Statistické testy pro nové účty
    correlation.png           - Korelace mezi metrikami
"""

import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from statsmodels.tsa.seasonal import STL
from scipy import stats

DB_CONFIG = {
    "host": "192.168.4.32",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "5452",  # <-- DOPLŇ
}

# Query pro nové účty (měsíčně - denně je příliš řídké)
QUERY_ACCOUNTS = """
SELECT
    date_trunc('month', account_created_at)::date AS datum,
    COUNT(*) AS nove_ucty
FROM users
WHERE account_created_at BETWEEN '2016-01-01' AND '2023-12-31'
  AND account_created_at IS NOT NULL
GROUP BY 1
ORDER BY 1;
"""

# Query pro achievement aktivitu (měsíčně pro srovnání)
QUERY_ACTIVITY = """
SELECT
    date_trunc('month', achievement_timestamp)::date AS datum,
    COUNT(*) AS aktivita
FROM activity_timeline
WHERE achievement_timestamp BETWEEN '2016-01-01' AND '2023-12-31'
GROUP BY 1
ORDER BY 1;
"""

# Klíčové události
EVENTS = [
    ("2020-03-01", "COVID\nlockdown", "#dc2626"),
    ("2021-12-01", "Konec\nopatření", "#dc2626"),
    ("2022-02-01", "Elden Ring", "#16a34a"),
    ("2023-09-01", "CS2 launch", "#9333ea"),
]


def fetch_data():
    print("Načítám data z databáze...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(QUERY_ACCOUNTS)
    accounts = pd.DataFrame(cur.fetchall(), columns=["datum", "nove_ucty"])
    accounts["datum"] = pd.to_datetime(accounts["datum"])
    accounts = accounts.set_index("datum")

    cur.execute(QUERY_ACTIVITY)
    activity = pd.DataFrame(cur.fetchall(), columns=["datum", "aktivita"])
    activity["datum"] = pd.to_datetime(activity["datum"])
    activity = activity.set_index("datum")

    cur.close()
    conn.close()

    # Spoj do jednoho DataFrame
    df = accounts.join(activity, how="inner")
    print(f"Načteno {len(df)} měsíců ({df.index.min().date()} až {df.index.max().date()})")
    print(f"Nové účty: {df['nove_ucty'].sum():,} celkem")
    print(f"Achievementy: {df['aktivita'].sum():,} celkem")
    return df


def plot_dual_axis(df):
    """Dual-axis graf: nové účty vlevo, aktivita vpravo."""
    fig, ax1 = plt.subplots(figsize=(14, 6), facecolor="white")

    # Nové účty - levá osa
    color1 = "#0284c7"
    ax1.bar(df.index, df["nove_ucty"], width=25,
            color=color1, alpha=0.6, label="Nové účty (měs.)")
    ax1.set_ylabel("Nové účty za měsíc", fontsize=11, color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)

    # Achievement aktivita - pravá osa
    ax2 = ax1.twinx()
    color2 = "#dc2626"
    ax2.plot(df.index, df["aktivita"], color=color2,
             linewidth=2, label="Achievement aktivita")
    ax2.set_ylabel("Achievementy za měsíc", fontsize=11, color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)

    # COVID zóna
    ax1.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-01"),
                alpha=0.1, color="#dc2626")
    ax1.text(pd.Timestamp("2020-09-01"), df["nove_ucty"].max() * 0.95,
             "COVID\nobdobí", fontsize=9, color="#dc2626",
             ha="center", fontweight="bold")

    # Anotace událostí
    for date_str, label, color in EVENTS:
        dt = pd.Timestamp(date_str)
        ax1.axvline(dt, color=color, linestyle="--", linewidth=1, alpha=0.6)

    # Legenda
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=10)

    ax1.set_title(
        "Nové Steam účty vs Achievement aktivita (2016–2023)\n"
        "Česká komunita, měsíční agregace",
        fontsize=13, fontweight="bold"
    )
    ax1.grid(axis="y", alpha=0.2, linestyle="--")
    ax1.spines["top"].set_visible(False)

    plt.tight_layout()
    plt.savefig("accounts_vs_activity.png", dpi=200,
                bbox_inches="tight", facecolor="white")
    print("Uloženo: accounts_vs_activity.png")
    plt.close()


def plot_stl_accounts(df):
    """STL dekompozice pro nové účty."""
    print("STL dekompozice nových účtů...")
    stl = STL(df["nove_ucty"], period=12, robust=True)
    result = stl.fit()

    fig, axes = plt.subplots(4, 1, figsize=(14, 10), facecolor="white")
    fig.suptitle(
        "STL dekompozice měsíčního vzniku nových účtů\n"
        "Česká Steam komunita 2016–2023",
        fontsize=13, fontweight="bold"
    )

    components = [
        (df["nove_ucty"], "Původní data", "#0284c7"),
        (result.trend, "Trend", "#0c4a6e"),
        (result.seasonal, "Sezónnost", "#16a34a"),
        (result.resid, "Residuály", "#888780"),
    ]

    for ax, (data, label, color) in zip(axes, components):
        ax.plot(data.index, data.values, color=color, linewidth=1.2)
        ax.set_ylabel(label, fontsize=10)
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-01"),
                   alpha=0.1, color="#dc2626")

    axes[-1].set_xlabel("Datum", fontsize=10)
    plt.tight_layout()
    plt.savefig("accounts_stl.png", dpi=200,
                bbox_inches="tight", facecolor="white")
    print("Uloženo: accounts_stl.png")
    plt.close()

    return result


def plot_correlation(df):
    """Scatter plot korelace mezi novými účty a aktivitou."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor="white")

    # Scatter: všechna data
    ax = axes[0]
    colors = []
    for dt in df.index:
        if pd.Timestamp("2020-03-01") <= dt <= pd.Timestamp("2021-12-01"):
            colors.append("#dc2626")
        elif dt < pd.Timestamp("2020-03-01"):
            colors.append("#0284c7")
        else:
            colors.append("#16a34a")

    ax.scatter(df["nove_ucty"], df["aktivita"],
               c=colors, alpha=0.7, s=50, edgecolors="white", linewidth=0.5)

    # Regresní přímka
    slope, intercept, r, p, se = stats.linregress(df["nove_ucty"], df["aktivita"])
    x_line = np.linspace(df["nove_ucty"].min(), df["nove_ucty"].max(), 100)
    ax.plot(x_line, slope * x_line + intercept,
            color="black", linewidth=1.5, linestyle="--",
            label=f"Regrese (r={r:.3f}, p={p:.4f})")

    ax.set_xlabel("Nové účty za měsíc", fontsize=11)
    ax.set_ylabel("Achievementy za měsíc", fontsize=11)
    ax.set_title("Korelace: Nové účty vs Aktivita", fontsize=12, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legenda barev
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#0284c7", label="Pre-COVID"),
        Patch(facecolor="#dc2626", label="COVID"),
        Patch(facecolor="#16a34a", label="Post-COVID"),
    ]
    ax.legend(handles=legend_elements, fontsize=9)

    # Cross-correlation (lag analýza)
    ax2 = axes[1]
    accounts_norm = (df["nove_ucty"] - df["nove_ucty"].mean()) / df["nove_ucty"].std()
    activity_norm = (df["aktivita"] - df["aktivita"].mean()) / df["aktivita"].std()

    lags = range(-12, 13)
    correlations = [accounts_norm.corr(activity_norm.shift(-lag)) for lag in lags]

    ax2.bar(lags, correlations,
            color=["#0284c7" if c > 0 else "#dc2626" for c in correlations])
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_xlabel("Zpoždění (měsíce)", fontsize=11)
    ax2.set_ylabel("Korelace", fontsize=11)
    ax2.set_title("Cross-korelace: Nové účty → Aktivita\n(lag analýza)",
                  fontsize=12, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3, linestyle="--")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig("correlation.png", dpi=200,
                bbox_inches="tight", facecolor="white")
    print("Uloženo: correlation.png")
    plt.close()

    return r, p, slope


def statistical_tests_accounts(df):
    """Statistické testy pro nové účty."""

    pre = df.loc["2018-01-01":"2020-03-01", "nove_ucty"]
    covid = df.loc["2020-03-01":"2021-12-01", "nove_ucty"]
    post = df.loc["2022-01-01":"2023-12-31", "nove_ucty"]

    u1, p1 = stats.mannwhitneyu(pre, covid, alternative="two-sided")
    u2, p2 = stats.mannwhitneyu(covid, post, alternative="two-sided")
    u3, p3 = stats.mannwhitneyu(pre, post, alternative="two-sided")

    # Pearson korelace mezi metrikami
    r_pearson, p_pearson = stats.pearsonr(df["nove_ucty"], df["aktivita"])
    r_spearman, p_spearman = stats.spearmanr(df["nove_ucty"], df["aktivita"])

    with open("accounts_stats.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("STATISTICKÉ TESTY: NOVÉ ÚČTY + KORELACE\n")
        f.write("=" * 60 + "\n\n")

        f.write("NOVÉ ÚČTY - MANN-WHITNEY U TEST\n")
        f.write("-" * 60 + "\n")

        for name, u, p in [
            ("Pre-COVID vs COVID", u1, p1),
            ("COVID vs Post-COVID", u2, p2),
            ("Pre-COVID vs Post-COVID", u3, p3),
        ]:
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            f.write(f"{name}: U={u:.0f}, p={p:.6f} {sig}\n")

        f.write("\n\nKORELACE: Nové účty vs Achievement aktivita\n")
        f.write("-" * 60 + "\n")
        f.write(f"Pearson r:  {r_pearson:.4f} (p={p_pearson:.6f})\n")
        f.write(f"Spearman r: {r_spearman:.4f} (p={p_spearman:.6f})\n")

        if abs(r_pearson) < 0.3:
            interp = "slabá korelace"
        elif abs(r_pearson) < 0.7:
            interp = "střední korelace"
        else:
            interp = "silná korelace"
        f.write(f"Interpretace: {interp}\n")

    with open("accounts_stats.txt", "r", encoding="utf-8") as f:
        print(f.read())


def main():
    df = fetch_data()
    plot_dual_axis(df)
    plot_stl_accounts(df)
    r, p, slope = plot_correlation(df)
    statistical_tests_accounts(df)

    print("\nHotovo! Výsledky:")
    print("  accounts_vs_activity.png - Dual-axis srovnání")
    print("  accounts_stl.png         - STL dekompozice účtů")
    print("  correlation.png          - Korelace + lag analýza")
    print("  accounts_stats.txt       - Statistické výsledky")


if __name__ == "__main__":
    main()
