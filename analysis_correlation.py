"""
analysis_correlation.py - Korelační analýza tří dvojic proměnných.

    A) Velikost knihovny vs. celkový odehraný čas
    B) Cena hry vs. počet unikátních hráčů
    C) Velikost knihovny vs. odhadovaná útrata

Výstup: outputs/correlation.txt, outputs/correlation_scatter.png
"""

from __future__ import annotations

from pathlib import Path

import db
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def _interpret_r(r: float) -> str:
    """Slovní interpretace síly korelace zdroj: http://geoinovace.data.quonia.cz/materialy/ZX510_Pokrocile_statisticke_metody_geografickeho_vyzkumu_MU/Korelacni_analyza.pdf."""
    abs_r = abs(r)
    if abs_r < 0.10:
        return "zanedbatelná"
    if abs_r < 0.30:
        return "slabá"
    if abs_r < 0.50:
        return "střední"
    if abs_r < 0.70:
        return "silná"
    return "velmi silná"


def _correlation_block(x: pd.Series, y: pd.Series, label_x: str, label_y: str) -> str:
    """Spočítá Pearson + Spearman a vrátí formátovaný text."""
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]

    r_p, p_p = stats.pearsonr(x, y)
    r_s, p_s = stats.spearmanr(x, y)

    return "\n".join(
        [
            f"{label_x} ↔ {label_y}",
            f"   n = {len(x):,}".replace(",", " "),
            f"   Pearson  r = {r_p:+.4f}  p = {p_p:.4g}  ({_interpret_r(r_p)})",
            f"   Spearman ρ = {r_s:+.4f}  p = {p_s:.4g}  ({_interpret_r(r_s)})",
        ]
    )


def run() -> None:
    users = db.load("user_stats")
    games = db.load("game_stats")

    report = [
        "=" * 70,
        "KORELAČNÍ ANALÝZA",
        "=" * 70,
        "",
        "Hladina významnosti: α = 0,05",
        "",
        "--- A) Počet vlastněných her vs. odehraný čas ---",
        "",
    ]

    active = users[users["games_owned"] > 0]
    report.append(
        _correlation_block(
            active["games_owned"],
            active["playtime_hours"],
            "Počet vlastněných her",
            "Odehraný čas (hodiny)",
        )
    )
    report.append("")

    report.append("--- B) Cena hry vs. počet unikátních hráčů ---")
    report.append("")
    paid = games[games["price_eur"] > 0]  # F2P tituly by vztah zkreslily
    report.append(
        _correlation_block(
            paid["price_eur"],
            paid["unique_players"],
            "Cena (EUR)",
            "Počet unikátních hráčů",
        )
    )
    report.append("")

    report.append("--- C) Počet vlastněných her vs. odhadovaná útrata ---")
    report.append("")
    report.append(
        _correlation_block(
            active["games_owned"],
            active["spend_eur"],
            "Počet vlastněných her",
            "Odhadovaná útrata (EUR)",
        )
    )
    report.append("")

    report.append("Pozn.: Data jsou silně sešikmená → Spearman je spolehlivější než Pearson.")

    text = "\n".join(report)
    print(text)
    (OUTPUT_DIR / "correlation.txt").write_text(text, encoding="utf-8")
    print(f"\n Uloženo do {OUTPUT_DIR / 'correlation.txt'}")

    _plot_scatters(active, paid)


def _plot_scatters(users: pd.DataFrame, games: pd.DataFrame) -> None:
    """Tři scatter ploty s log škálami (jinak outliery zničí čitelnost)."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # A) games_owned vs. playtime
    ax = axes[0]
    ax.scatter(users["games_owned"], users["playtime_hours"], s=4, alpha=0.3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Vlastněné hry (log)")
    ax.set_ylabel("Odehraný čas v hodinách (log)")
    ax.set_title("A) Knihovna vs. odehraný čas")
    ax.grid(alpha=0.3)

    # B) cena vs. počet hráčů
    ax = axes[1]
    ax.scatter(games["price_eur"], games["unique_players"], s=4, alpha=0.3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Cena EUR (log)")
    ax.set_ylabel("Unikátní hráči (log)")
    ax.set_title("B) Cena vs. popularita")
    ax.grid(alpha=0.3)

    # C) games_owned vs. spend
    ax = axes[2]
    ax.scatter(users["games_owned"], users["spend_eur"], s=4, alpha=0.3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Vlastněné hry (log)")
    ax.set_ylabel("Odhad útraty EUR (log)")
    ax.set_title("C) Knihovna vs. útrata")
    ax.grid(alpha=0.3)

    fig.suptitle("Korelační scatter ploty (logaritmické osy)")
    fig.tight_layout()
    out = OUTPUT_DIR / "correlation_scatter.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Graf uložen do {out}")


if __name__ == "__main__":
    run()
