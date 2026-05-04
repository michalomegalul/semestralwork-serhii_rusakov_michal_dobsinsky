"""
db.py - Data.

Jediné místo, které sahá na PostgreSQL. Stáhne všechny agregace
potřebné pro kapitolu 4 jedním průchodem a uloží je do
CSV cache v adresáři data/. Další běhy už DB nezatěžují.

Použití:
    python db.py              # stáhne vše a uloží do data/*.csv
    python db.py --refresh    # vynutí stažení i když cache existuje
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


QUERIES: dict[str, str] = {
    "daily_activity": """
        WITH days AS (
            SELECT generate_series(
                DATE '2016-01-01',
                DATE '2025-12-31',
                INTERVAL '1 day'
            )::date AS day
        ),
        counts AS (
            SELECT
                date_trunc('day', achievement_timestamp)::date AS day,
                COUNT(*) AS achievements
            FROM Activity_Timeline
            WHERE achievement_timestamp >= DATE '2016-01-01'
              AND achievement_timestamp <  DATE '2026-01-01'
            GROUP BY 1
        )
        SELECT
            d.day,
            COALESCE(c.achievements, 0) AS achievements
        FROM days d
        LEFT JOIN counts c USING (day)
        ORDER BY d.day;
    """,
    # --------------------------------------------------------------------
    # Charakteristiky uživatelů: vlastněné hry a aproximovaná útrata.
    # Vstup pro korelační analýzu (počet her vs. odehraný čas, cena vs. popularita).
    # --------------------------------------------------------------------
    "user_stats": """
        SELECT
            u.steam_id,
            COUNT(DISTINCT ul.app_id)                          AS games_owned,
            COALESCE(SUM(ul.total_playtime_minutes), 0) / 60.0 AS playtime_hours,
            COALESCE(SUM(g.historical_low_price), 0)           AS spend_eur
        FROM Users u
        LEFT JOIN User_Library ul ON ul.steam_id = u.steam_id
        LEFT JOIN Games g         ON g.app_id    = ul.app_id
        GROUP BY u.steam_id;
    """,
    # --------------------------------------------------------------------
    # Per-game agregace pro analýzu cena ku popularita.
    # --------------------------------------------------------------------
    "game_stats": """
        SELECT
            g.app_id,
            g.title,
            g.historical_low_price        AS price_eur,
            COUNT(DISTINCT ul.steam_id)   AS unique_players,
            COALESCE(SUM(ul.total_playtime_minutes), 0) / 60.0 AS total_hours
        FROM Games g
        LEFT JOIN User_Library ul ON ul.app_id = g.app_id
        WHERE g.historical_low_price IS NOT NULL
        GROUP BY g.app_id, g.title, g.historical_low_price
        HAVING COUNT(DISTINCT ul.steam_id) >= 10
        ORDER BY unique_players DESC;
    """,
}


def get_connection() -> psycopg2.extensions.connection:
    """Connection s heslem z env proměnné."""
    password = os.environ.get("PG_PASSWORD")
    if not password:
        sys.exit(" Chybí PG_PASSWORD.\n")

    return psycopg2.connect(
        dbname=os.environ.get("PG_DBNAME", "postgres"),
        user=os.environ.get("PG_USER", "postgres"),
        password=password,
        host=os.environ.get("PG_HOST", "192.168.4.32"),
        port=os.environ.get("PG_PORT", "5432"),
    )


def fetch_all(refresh: bool = False) -> dict[str, pd.DataFrame]:
    """
    Stáhne všechny dotazy a uloží do CSV. Pokud cache existuje a refresh=False,
    načítá z disku.
    """
    results: dict[str, pd.DataFrame] = {}

    need_db = refresh or any(
        not (DATA_DIR / f"{name}.csv").exists() for name in QUERIES
    )

    if not need_db:
        print("Načítám z cache (data/*.csv). Použij --refresh pro nové stažení.")
        for name in QUERIES:
            results[name] = pd.read_csv(DATA_DIR / f"{name}.csv")
        return results

    print("🔌 Připojuji se k DB...")
    with get_connection() as conn:
        for name, sql in QUERIES.items():
            print(f"   → {name} ...", end=" ", flush=True)
            df = pd.read_sql(sql, conn)
            df.to_csv(DATA_DIR / f"{name}.csv", index=False)
            print(f"{len(df):,} řádků")
            results[name] = df

    print("Hotovo. Cache uložena v data/")
    return results


def load(name: str) -> pd.DataFrame:
    """
    Helper pro analytické moduly. Načte konkrétní tabulku z cache.
    Pokud cache neexistuje, stáhne ji.
    """
    csv_path = DATA_DIR / f"{name}.csv"
    if not csv_path.exists():
        fetch_all()
    df = pd.read_csv(csv_path)
    for col in df.columns:
        if col in ("day", "date", "achievement_timestamp"):
            df[col] = pd.to_datetime(df[col])
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh", action="store_true", help="Vynutit nové stažení z DB"
    )
    args = parser.parse_args()
    fetch_all(refresh=args.refresh)
