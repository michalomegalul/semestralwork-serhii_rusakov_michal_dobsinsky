"""
STL dekompozice časové řady a statistické testování COVID efektu.

Použití:
    pip install psycopg2-binary matplotlib pandas numpy statsmodels scipy --break-system-packages
    python3 stl_covid.py

Výstupy:
    stl_decomposition.png  - STL dekompozice (trend, sezónnost, residuály)
    covid_trend.png        - Trend s COVID anotací a statistickým testem
    covid_stats.txt        - Výsledky statistických testů
"""

import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from statsmodels.tsa.seasonal import STL
from scipy import stats

DB_CONFIG = {
    "host": "192.168.4.32",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "5452",  # <-- DOPLŇ
}

QUERY = """
SELECT
    date_trunc('day', achievement_timestamp)::date AS datum,
    COUNT(*) AS aktivita
FROM activity_timeline
WHERE achievement_timestamp BETWEEN '2016-01-01' AND '2023-12-31'
GROUP BY 1
ORDER BY 1;
"""

# Klíčové události pro anotaci
EVENTS = [
    ("2020-03-12", "COVID\nlockdown CZ", "#dc2626"),
    ("2021-12-01", "COVID\nkonec opatření", "#dc2626"),
    ("2017-06-09", "Steam\nSummer Sale", "#2563eb"),
    ("2022-02-25", "Elden Ring\nlaunch", "#16a34a"),
    ("2023-09-27", "CS2\nlaunch", "#9333ea"),
]


def fetch_data():
    print("Připojuji se k databázi...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(QUERY)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    df = pd.DataFrame(rows, columns=["datum", "aktivita"])
    df["datum"] = pd.to_datetime(df["datum"])
    df = df.set_index("datum")

    # Doplň chybějící dny nulou
    full_range = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_range, fill_value=0)
    df.index.name = "datum"

    print(f"Načteno {len(df)} dnů dat ({df.index.min().date()} až {df.index.max().date()})")
    return df


def remove_spam_outliers(df):
    """Odstraní achievement spam outliers (nahradí mediánem okolí)."""
    spam_dates = ["2021-11-13", "2018-09-04", "2018-04-15", "2019-03-17"]
    df = df.copy()
    for d in spam_dates:
        if pd.Timestamp(d) in df.index:
            # Nahraď průměrem 7 dnů okolo
            window = df.loc[
                pd.Timestamp(d) - pd.Timedelta(days=7):
                pd.Timestamp(d) + pd.Timedelta(days=7)
            ]["aktivita"]
            df.loc[pd.Timestamp(d), "aktivita"] = window.median()
            print(f"Odstraněn outlier: {d}")
    return df


def run_stl(df):
    """Spustí STL dekompozici s týdenní a roční periodicitou."""
    print("Spouštím STL dekompozici...")
    # Perioda 365 = roční sezónnost
    stl = STL(df["aktivita"], period=365, robust=True)
    result = stl.fit()
    return result


def plot_stl(df, stl_result):
    """Vykreslí 4-panelový STL dekompozici."""
    fig, axes = plt.subplots(4, 1, figsize=(14, 12), facecolor="white")
    fig.suptitle(
        "STL dekompozice denní achievement aktivity\n"
        "Česká Steam komunita 2016–2023",
        fontsize=14, fontweight="bold"
    )

    components = [
        (df["aktivita"], "Původní data", "#378ADD"),
        (stl_result.trend, "Trend", "#0c4a6e"),
        (stl_result.seasonal, "Sezónnost", "#16a34a"),
        (stl_result.resid, "Residuály", "#888780"),
    ]

    for ax, (data, label, color) in zip(axes, components):
        ax.plot(data.index, data.values, color=color, linewidth=0.8, alpha=0.9)
        ax.set_ylabel(label, fontsize=10)
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # COVID šedá zóna na každém panelu
        ax.axvspan(
            pd.Timestamp("2020-03-12"),
            pd.Timestamp("2021-12-01"),
            alpha=0.1, color="#dc2626", label="COVID období"
        )

    axes[-1].set_xlabel("Datum", fontsize=10)
    axes[0].legend(["Aktivita", "COVID období"], loc="upper left", fontsize=9)

    plt.tight_layout()
    plt.savefig("stl_decomposition.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Uloženo: stl_decomposition.png")
    plt.close()


def plot_trend_with_events(stl_result):
    """Vykreslí trend s anotacemi klíčových událostí."""
    fig, ax = plt.subplots(figsize=(14, 6), facecolor="white")

    trend = stl_result.trend

    # Trend čára
    ax.plot(trend.index, trend.values,
            color="#0c4a6e", linewidth=2, label="Trend aktivity")

    # COVID šedá zóna
    ax.axvspan(
        pd.Timestamp("2020-03-12"),
        pd.Timestamp("2021-12-01"),
        alpha=0.15, color="#dc2626"
    )
    ax.text(
        pd.Timestamp("2020-08-01"), trend.max() * 0.97,
        "COVID\nobdobí",
        fontsize=9, color="#dc2626", ha="center", fontweight="bold"
    )

    # Anotace událostí
    y_min, y_max = trend.min(), trend.max()
    y_range = y_max - y_min

    for date_str, label, color in EVENTS:
        dt = pd.Timestamp(date_str)
        if dt in trend.index:
            val = trend[dt]
        else:
            # Najdi nejbližší datum
            idx = trend.index.get_indexer([dt], method="nearest")[0]
            val = trend.iloc[idx]
            dt = trend.index[idx]

        ax.axvline(dt, color=color, linestyle="--", linewidth=1.2, alpha=0.7)
        ax.text(dt, y_max + y_range * 0.05, label,
                fontsize=8, color=color, ha="center", va="bottom", rotation=0)

    ax.set_xlabel("Datum", fontsize=11)
    ax.set_ylabel("Průměrná denní aktivita (achievementy)", fontsize=11)
    ax.set_title(
        "Trend achievement aktivity s klíčovými událostmi\n"
        "STL dekompozice, Česká Steam komunita 2016–2023",
        fontsize=13, fontweight="bold", pad=20
    )
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    plt.savefig("covid_trend.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Uloženo: covid_trend.png")
    plt.close()


def statistical_tests(df):
    """Provede statistické testy pro COVID efekt."""
    print("\nProvádím statistické testy...")

    # Definuj období
    pre_covid = df.loc["2018-01-01":"2020-03-11", "aktivita"]
    covid = df.loc["2020-03-12":"2021-12-01", "aktivita"]
    post_covid = df.loc["2022-01-01":"2023-12-31", "aktivita"]

    results = {}

    # Základní statistiky
    for name, period in [("Pre-COVID", pre_covid),
                          ("COVID", covid),
                          ("Post-COVID", post_covid)]:
        results[name] = {
            "n_days": len(period),
            "mean": period.mean(),
            "median": period.median(),
            "std": period.std(),
            "cv": period.std() / period.mean() * 100,
        }

    # Mann-Whitney U test (neparametrický, lepší pro nonnormální data)
    u_stat_1, p_val_1 = stats.mannwhitneyu(pre_covid, covid, alternative="two-sided")
    u_stat_2, p_val_2 = stats.mannwhitneyu(covid, post_covid, alternative="two-sided")
    u_stat_3, p_val_3 = stats.mannwhitneyu(pre_covid, post_covid, alternative="two-sided")

    # Cohen's d pro velikost efektu
    def cohens_d(a, b):
        pooled_std = np.sqrt((a.std()**2 + b.std()**2) / 2)
        return (b.mean() - a.mean()) / pooled_std

    d_pre_covid = cohens_d(pre_covid, covid)
    d_covid_post = cohens_d(covid, post_covid)
    d_pre_post = cohens_d(pre_covid, post_covid)

    # Ulož výsledky do txt
    with open("covid_stats.txt", "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("STATISTICKÉ TESTOVÁNÍ COVID EFEKTU\n")
        f.write("Achievement aktivita, Česká Steam komunita\n")
        f.write("=" * 60 + "\n\n")

        f.write("POPISNÁ STATISTIKA PODLE OBDOBÍ\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Statistika':<20} {'Pre-COVID':>12} {'COVID':>12} {'Post-COVID':>12}\n")
        f.write("-" * 60 + "\n")

        for stat, label in [("n_days", "Počet dní"),
                              ("mean", "Průměr"),
                              ("median", "Medián"),
                              ("std", "Std. odchylka"),
                              ("cv", "CV (%)")]:
            row = f"{label:<20}"
            for period in ["Pre-COVID", "COVID", "Post-COVID"]:
                val = results[period][stat]
                row += f" {val:>12.2f}"
            f.write(row + "\n")

        f.write("\n\nMANN-WHITNEY U TEST (neparametrický)\n")
        f.write("-" * 60 + "\n")
        f.write("H0: Rozdělení aktivity v obou obdobích je stejné\n\n")

        tests = [
            ("Pre-COVID vs COVID", u_stat_1, p_val_1, d_pre_covid),
            ("COVID vs Post-COVID", u_stat_2, p_val_2, d_covid_post),
            ("Pre-COVID vs Post-COVID", u_stat_3, p_val_3, d_pre_post),
        ]

        for name, u, p, d in tests:
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
            f.write(f"{name}\n")
            f.write(f"  U statistika: {u:.0f}\n")
            f.write(f"  p-hodnota:    {p:.6f} {sig}\n")
            f.write(f"  Cohen's d:    {d:.3f} ")
            if abs(d) < 0.2:
                f.write("(zanedbatelný efekt)\n")
            elif abs(d) < 0.5:
                f.write("(malý efekt)\n")
            elif abs(d) < 0.8:
                f.write("(střední efekt)\n")
            else:
                f.write("(velký efekt)\n")
            f.write("\n")

        f.write("Hladiny významnosti: * p<0.05, ** p<0.01, *** p<0.001, ns = nevýznamné\n")

    print("Uloženo: covid_stats.txt")

    # Vytiskni výsledky i do konzole
    with open("covid_stats.txt", "r", encoding="utf-8") as f:
        print(f.read())

    return results


def plot_period_comparison(df):
    """Box plot srovnání aktivit mezi obdobími."""
    pre_covid = df.loc["2018-01-01":"2020-03-11", "aktivita"]
    covid = df.loc["2020-03-12":"2021-12-01", "aktivita"]
    post_covid = df.loc["2022-01-01":"2023-12-31", "aktivita"]

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")

    bp = ax.boxplot(
        [pre_covid, covid, post_covid],
        labels=["Pre-COVID\n(2018–03/2020)", "COVID\n(03/2020–12/2021)", "Post-COVID\n(2022–2023)"],
        patch_artist=True,
        medianprops=dict(color="black", linewidth=2),
        flierprops=dict(marker="o", markersize=2, alpha=0.3)
    )

    colors = ["#bae6fd", "#fca5a5", "#bbf7d0"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)

    # Přidej průměry jako diamanty
    for i, period in enumerate([pre_covid, covid, post_covid], 1):
        ax.scatter(i, period.mean(), marker="D", color="#1e40af",
                   s=50, zorder=5, label="Průměr" if i == 1 else "")

    ax.set_ylabel("Denní počet achievementů", fontsize=11)
    ax.set_title(
        "Srovnání denní achievement aktivity podle období\n"
        "Box plot s průměrem (♦)",
        fontsize=13, fontweight="bold"
    )
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig("covid_boxplot.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Uloženo: covid_boxplot.png")
    plt.close()


def main():
    # 1. Načti data
    df = fetch_data()

    # 2. Odstraň achievement spam outliers
    df = remove_spam_outliers(df)

    # 3. STL dekompozice
    stl_result = run_stl(df)

    # 4. Grafy
    plot_stl(df, stl_result)
    plot_trend_with_events(stl_result)
    plot_period_comparison(df)

    # 5. Statistické testy
    statistical_tests(df)

    print("\nHotovo! Vygenerované soubory:")
    print("  stl_decomposition.png - STL dekompozice")
    print("  covid_trend.png       - Trend s událostmi")
    print("  covid_boxplot.png     - Box plot srovnání období")
    print("  covid_stats.txt       - Výsledky statistických testů")


if __name__ == "__main__":
    main()
