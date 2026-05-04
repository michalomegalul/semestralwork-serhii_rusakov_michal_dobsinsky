# CLAUDE.md — Semestrální práce VŠE

## What this is

Semestral project for **VŠE Praha, FIS, Data Analytics program**. Authors: Serhii Rusakov & Michal Dobšínský. Supervisor: Ing. Jan Zeman, Ph.D. Due: April 2026.

**Topic:** Statistical analysis of Czech Steam users' activity 2016–2025, with focus on whether COVID-19 left a measurable signal in the data.

**Repo:** https://github.com/michalomegalul/semestralwork-serhii_rusakov_michal_dobsinsky

## The data

PostgreSQL database (host: `192.168.4.32`). Four tables:

| Table | Rows | Key columns |
|-------|------|-------------|
| `Users` | ~48k | `steam_id`, `account_created_at`, `total_games_owned` |
| `Games` | ~20k | `app_id`, `title`, `historical_low_price`, `currency` |
| `User_Library` | ~1.5M | `steam_id`, `app_id`, `total_playtime_minutes` |
| `Activity_Timeline` | ~3.5M | `steam_id`, `app_id`, `achievement_timestamp` |

Connection requires `PG_PASSWORD` env var. **Never put the password in code.**

## Project layout

```
semestralka/
├── CLAUDE.md                      ← this file (read every session)
├── CONTEXT.md                     ← current state, what's next
├── README.md                      ← setup + run instructions
├── requirements.txt
├── .gitignore
├── .env                           ← secrets (gitignored, never commit)
│
├── db.py                          ← SQL aggregations + CSV cache
├── periods.py                     ← pre/covid/post period definitions
├── analysis_anova.py              ← Shapiro + Levene + ANOVA + Kruskal + Tukey
├── analysis_chi_square.py         ← day-of-week uniformity test
├── analysis_correlation.py        ← Pearson + Spearman, 3 hypotheses
├── analysis_stl.py                ← seasonal-trend decomposition
├── analysis_changepoint.py        ← PELT + Binary segmentation
├── main.py                        ← runs all analyses in order
├── organize.py                    ← housekeeping script (see "Housekeeping")
│
├── data/                          ← CSV cache (gitignored, do not touch)
├── outputs/                       ← reports + plots for the paper
├── drafts/                        ← Word drafts (gitignored)
├── archive/                       ← old runs, sorted by date (gitignored)
│
├── scripts/                       ← data collection + one-off tools
│   ├── steam_api_sniffer_CZ.py    ← Czech Steam ID collector
│   ├── steam_api_sniffer.py       ← generic sniffer
│   ├── steam_api_data.py
│   ├── steam_api_test.py
│   ├── db_migration.py            ← DB dedup migration (run once)
│   ├── test.py
│   └── legacy/                    ← early prototypes (superseded)
│       ├── Heatmap.py
│       ├── stats.py
│       └── top10dnu.py
│
└── .claude/
    └── rules/
        └── analysis.md            ← path-scoped rules for analysis_*.py
```

## How to run things

```bash
source venv/bin/activate
export PG_PASSWORD='...'      # never commit this
python main.py                # cached run
python main.py --refresh      # re-fetch from DB
python organize.py            # tidy outputs/, see Housekeeping below
```

Each `analysis_*.py` is also runnable standalone. They all read from `data/*.csv`, write to `outputs/`.

## Conventions

- **Language for code comments and report text: Czech.** Variable names and function names: English.
- **Docstrings: Czech.** It's a Czech-language thesis; consistency matters for the supervisor.
- **Commit messages: English** (so the repo reads cleanly on GitHub).
- **Decimal separator in the report text: comma** (Czech standard: `0,05` not `0.05`). In code and CSVs: dot.
- **Significance level: α = 0,05** unless explicitly stated otherwise.
- **Three COVID periods are DEFINED IN ONE PLACE** (`periods.py`). Never hardcode date ranges in analysis modules — always import from there.

## Statistical rigor — non-negotiable

These rules exist because the supervisor will check them at the defense:

1. **Always test ANOVA assumptions before reporting ANOVA results.** Shapiro-Wilk for normality, Levene for variance homogeneity. If either fails, Kruskal-Wallis is the primary test, ANOVA is reference only. The current `analysis_anova.py` does this automatically — don't bypass it.
2. **Report effect size alongside p-values.** η² for ANOVA, ε² for Kruskal-Wallis, Cramér's V for chi-square, r/ρ for correlations. p alone is not enough.
3. **Period definitions must be disjoint.** No overlap between pre-COVID, COVID, and post-COVID. February 2020 is intentionally in the buffer (no COVID restrictions in CZ yet).
4. **Cite the standard.** APA 7 (per VŠE FIS guidelines).

## Security

- `PG_PASSWORD` lives in env, never in code, never in git.
- `data/` is gitignored — Steam IDs are personal data (GDPR territory).
- The original `desk.docx` contained the password `5452`. **That password must be considered compromised** — change it on the actual database.
- If you find any other credential in the repo, treat it as leaked and rotate it.

## Housekeeping

Run `python organize.py` to:
- Move `outputs/*` older than 7 days into `archive/YYYY-MM-DD/`
- Re-render the index of latest results into `outputs/INDEX.md`
- List orphan files (no matching analysis script)

Run before every commit, or when `outputs/` gets cluttered after multiple `--refresh` runs.

## When asked to add a new analysis

1. Create `analysis_<name>.py` matching the pattern of existing ones (load via `db.load`, write to `outputs/`, produce both `.txt` and `.png`).
2. Register it in `main.py`'s `STEPS` list.
3. Add a one-line entry to the table in `README.md` under "Co kam patří v textu práce".
4. Update `CONTEXT.md` if it changes the active work or open questions.

## What NOT to do

- Don't write to `data/` — it's a read-only cache from DB perspective.
- Don't commit `data/` or `outputs/large_files` — gitignore is set, keep it that way.
- Don't refactor the SQL in `db.py` without checking that the cache filenames still match what analyses expect.
- Don't add `print()` statements to analysis files for debugging and forget to remove them. Use `logging` if needed.
- Don't auto-generate the report text in Word. The thesis must reflect our own analysis and interpretation — Claude helps with structure and method, not with claims about the data.
