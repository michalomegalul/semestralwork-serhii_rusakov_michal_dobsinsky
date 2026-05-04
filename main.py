"""
main.py - Spustí všechny analytické moduly v rozumném pořadí.

Použití:
    export PG_PASSWORD='vaše_heslo'
    python main.py             # použije cache pokud existuje
    python main.py --refresh   # vynutí stažení dat z DB
"""
from __future__ import annotations

import argparse
import time

import db
import analysis_anova
import analysis_chi_square
import analysis_correlation
import analysis_stl
import analysis_changepoint


STEPS = [
    ("Chi-square (dny v týdnu)",   analysis_chi_square.run),
    ("Korelační analýza",          analysis_correlation.run),
    ("ANOVA + post-hoc",           analysis_anova.run),
    ("STL dekompozice",            analysis_stl.run),
    ("Detekce bodů změny",         analysis_changepoint.run),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true",
                        help="Stáhnout data z DB znovu")
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("SEMESTRÁLNÍ PRÁCE — KOMPLETNÍ ANALÝZA")
    print("=" * 70)

    db.fetch_all(refresh=args.refresh)

    for i, (name, fn) in enumerate(STEPS, 1):
        print(f"\n\n{'#' * 70}")
        print(f"# KROK {i}/{len(STEPS)}: {name}")
        print(f"{'#' * 70}\n")
        t0 = time.time()
        fn()
        print(f"\n⏱  {name}: {time.time() - t0:.1f}s")

    print("\n" + "=" * 70)
    print("✅ HOTOVO. Všechny výstupy v adresáři outputs/")
    print("=" * 70)


if __name__ == "__main__":
    main()
