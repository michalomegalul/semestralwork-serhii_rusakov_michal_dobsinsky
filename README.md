# Semestrální práce — analytická vrstva

Sedm statistických metod, jeden centrální datový pipeline. Vše v Pythonu,
agregace tahané z DB jediným SQL na metodu.

## Setup

```bash
# 1. Vytvoř VE
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate     # Windows

# 2. Nainstaluj závislosti
pip install -r requirements.txt
```

## Spuštění

```bash
# Vše najednou (stáhne data + spustí všech 5 analýz)
python main.py

# První spuštění s refresh, pak už z cache:
python main.py --refresh

# Jednotlivé analýzy:
python analysis_anova.py        # Kapitola 4 — hlavní
python analysis_chi_square.py   # Kapitola 3 — dny v týdnu
python analysis_correlation.py  # Kapitola 2 — vztahy
python analysis_stl.py          # Kapitola 3 — sezónnost
python analysis_changepoint.py  # Kapitola 4 — body změny
```

## Struktura

```
semestralka/
├── db.py                       # SQL agregace + CSV cache
├── periods.py                  # Definice 3 období (pre/covid/post)
├── analysis_anova.py           # Shapiro + Levene + ANOVA + Kruskal + Tukey
├── analysis_chi_square.py      # Test rovnoměrnosti dnů v týdnu
├── analysis_correlation.py     # Pearson + Spearman, 3 dvojice
├── analysis_stl.py             # Trend / sezónnost / reziduum
├── analysis_changepoint.py     # PELT + Binseg
├── main.py                     # Zapne pro vše
├── data/                       # CSV cache
└── outputs/                    # Reporty + grafy
```

## Co patří kam

| Soubor v outputs/         | Kapitola práce |
|---------------------------|----------------|
| `chi_square_dow.txt`      | 3.1 (Tab. 3.1 — doplnit p-hodnotu a χ²) |
| `correlation.txt` + `.png`| 2.1, 2.4 (nová podkapitola) |
| `anova_results.txt`       | 4.2 — 4.4 (úplná reformulace) |
| `anova_boxplot.png`       | 4.3 (Obr. 4.1) |
| `stl_decomposition.png`   | 3.2 (Obr. 3.1) |
| `stl_results.txt`         | 3.3 (anomálie — místo TODO) |
| `changepoint.png` + `.txt`| 4.5 (Obr. 4.2) |
