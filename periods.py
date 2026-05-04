"""
periods.py - Definice období pro analýzu vlivu COVID-19.

Tři DISJUNKTNÍ období (žádný překryv → ANOVA dává smysl):
    - pre_covid:  2016-01-01 až 2019-12-31  (4 roky před)
    - covid:      2020-03-01 až 2021-12-31  (od WHO vyhlášení pandemie)
    - post_covid: 2022-01-01 až 2025-12-31  (4 roky po)

Pozn.: Rok 2020-leden a 2020-únor záměrně vynecháváme, protože
v Česku ještě nebyla zavedena žádná opatření a nárůst je až od března.
Tento "buffer" je potřeba zmínit v textu jako součást metodiky.
"""

from __future__ import annotations

import pandas as pd

PERIODS = {
    "pre_covid": ("2016-01-01", "2019-12-31"),
    "covid": ("2020-03-01", "2021-12-31"),
    "post_covid": ("2022-01-01", "2025-12-31"),
}

# České popisky pro grafy a tabulky.
LABELS = {
    "pre_covid": "Pre-COVID (2016–2019)",
    "covid": "COVID (březen 2020 – 2021)",
    "post_covid": "Post-COVID (2022–2025)",
}


def assign_period(date_series: pd.Series) -> pd.Series:
    """Přiřadí každému datu jeho období (NaN pokud spadá do bufferu led-úno 2020)."""
    result = pd.Series(index=date_series.index, dtype="object")
    for name, (start, end) in PERIODS.items():
        mask = (date_series >= start) & (date_series <= end)
        result[mask] = name
    return result
