"""
Top 10 nejaktivnějších dnů v roce - horizontální bar chart.
Vánoční období je zvýrazněno odlišnou barvou.

Použití:
    pip install psycopg2-binary matplotlib --break-system-packages
    python3 top_days.py
"""

import psycopg2
import matplotlib.pyplot as plt

DB_CONFIG = {
    "host": "192.168.4.32",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres",
    "password": "5452",  # <-- DOPLŇ
}

QUERY = """
SELECT
    EXTRACT(MONTH FROM achievement_timestamp)::int AS mesic,
    EXTRACT(DAY FROM achievement_timestamp)::int AS den,
    ROUND(AVG(daily_count))::int AS prumer
FROM (
    SELECT
        date_trunc('day', achievement_timestamp) AS d,
        achievement_timestamp,
        COUNT(*) OVER (PARTITION BY date_trunc('day', achievement_timestamp)) AS daily_count
    FROM activity_timeline
    WHERE achievement_timestamp BETWEEN '2016-01-01' AND '2026-12-31'
) sub
GROUP BY 1, 2
ORDER BY prumer DESC
LIMIT 10;
"""

MONTH_NAMES_GENITIV = {
    1: "ledna", 2: "února", 3: "března", 4: "dubna",
    5: "května", 6: "června", 7: "července", 8: "srpna",
    9: "září", 10: "října", 11: "listopadu", 12: "prosince"
}


def fetch_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(QUERY)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def main():
    print("Stahuji data...")
    rows = fetch_data()

    # Připrav data - obrátíme pořadí aby největší byl nahoře v grafu
    rows = list(reversed(rows))
    labels = [f"{int(d)}. {MONTH_NAMES_GENITIV[int(m)]}" for m, d, _ in rows]
    values = [int(v) for _, _, v in rows]

    # Vánoční období = barva tmavě červená, ostatní = modrá
    colors = []
    for m, d, _ in rows:
        if int(m) == 12 and int(d) >= 24:
            colors.append("#dc2626")  # vánoční - červená
        else:
            colors.append("#378ADD")  # ostatní - modrá

    fig, ax = plt.subplots(figsize=(11, 6.5), facecolor="white")

    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.5)

    # Hodnoty na konci sloupců
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 50, bar.get_y() + bar.get_height() / 2,
                f"{val:,}".replace(",", " "),
                va="center", fontsize=10, color="#333")

    # Průměrná denní aktivita = referenční čára
    avg_daily = 950
    ax.axvline(avg_daily, color="#888", linestyle="--", linewidth=1.5,
               label=f"Běžný denní průměr ({avg_daily})", alpha=0.7)

    ax.set_xlabel("Průměrná denní aktivita (počet achievementů)", fontsize=11)
    ax.set_title("Top 10 nejaktivnějších dnů v roce\n"
                 "Průměr z let 2016–2026, červeně vánoční období",
                 fontsize=13, fontweight="bold", pad=15)

    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=10)

    # Skryj horní a pravý rámeček
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Formát čísel s mezerou
    ax.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: f"{int(x):,}".replace(",", " ")
    ))

    # Padding pro popisky hodnot napravo
    ax.set_xlim(0, max(values) * 1.12)

    plt.tight_layout()
    plt.savefig("top_days.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Uloženo: top_days.png")


if __name__ == "__main__":
    main()
