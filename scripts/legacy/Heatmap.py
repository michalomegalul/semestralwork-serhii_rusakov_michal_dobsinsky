"""
Jednoduchá 4×3 heatmapa - jedna buňka = jeden měsíc.
Hodnota = celkový počet achievementů za daný měsíc (sečteno přes roky 2016-2023).

Použití:
    pip install psycopg2-binary matplotlib --break-system-packages
    python3 heatmap_months_4x3.py
"""

import psycopg2
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

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
    COUNT(*) AS celkem
FROM activity_timeline
WHERE achievement_timestamp BETWEEN '2016-01-01' AND '2026-1-1'
GROUP BY 1
ORDER BY 1;
"""

def fetch_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(QUERY)
    data = {m: v for m, v in cur.fetchall()}
    cur.close()
    conn.close()
    return data


def main():
    print("Stahuji data...")
    data = fetch_data()

    months_cz = ["Leden", "Únor", "Březen", "Duben",
                 "Květen", "Červen", "Červenec", "Srpen",
                 "Září", "Říjen", "Listopad", "Prosinec"]

    # Naplň 4x3 matici hodnotami
    grid = np.zeros((4, 3))
    for i in range(12):
        row = i // 3
        col = i % 3
        grid[row, col] = data.get(i + 1, 0)

    # Spočítej procenta z celkového součtu
    total = grid.sum()
    percentages = (grid / total * 100)

    # Cmap - modré odstíny
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "blues",
        ["#f0f9ff", "#bae6fd", "#7dd3fc", "#38bdf8", "#0284c7", "#0c4a6e"]
    )

    fig, ax = plt.subplots(figsize=(10, 8), facecolor="white")

    im = ax.imshow(grid, cmap=cmap, aspect="auto")

    # Popisky uvnitř buněk: název měsíce + hodnota + procento
    vmin, vmax = grid.min(), grid.max()
    for i in range(12):
        row = i // 3
        col = i % 3
        val = grid[row, col]
        pct = percentages[row, col]
        norm_val = (val - vmin) / (vmax - vmin) if vmax > vmin else 0
        text_color = "white" if norm_val > 0.55 else "#1a1a1a"

        ax.text(col, row - 0.25, months_cz[i],
                ha="center", va="center",
                fontsize=14, fontweight="600", color=text_color)
        ax.text(col, row + 0.05, f"{int(val):,}".replace(",", " "),
                ha="center", va="center",
                fontsize=11, color=text_color)
        ax.text(col, row + 0.28, f"{pct:.2f} %".replace(".", ","),
                ha="center", va="center",
                fontsize=11, fontweight="600", color=text_color)

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title("Aktivita podle měsíce (2016–2023)\nCelkový počet achievementů",
              fontsize=14, fontweight="bold", pad=15)

    # Barevná lišta
    cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Počet achievementů", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    plt.tight_layout()
    plt.savefig("heatmap_months_4x3.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Uloženo: heatmap_months_4x3.png")


if __name__ == "__main__":
    main()
