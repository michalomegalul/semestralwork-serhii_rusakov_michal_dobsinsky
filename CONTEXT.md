# CONTEXT.md — Current state

> **This file is for what's CURRENTLY happening.** Update it at the end of each work session. CLAUDE.md is for the stable rules; this is for the moving parts.

Last updated: 2026-05-04

## Where we are

Analytical pipeline (5 modules) is implemented and smoke-tested on synthetic data. Awaiting first run on production DB.

The thesis text in `desk.docx` has the structure right but Chapter 4 ("Covid a porovnani s událostmi") is mostly TODO placeholders. Filling those in is the next big task once we have real numbers.

## Recently done (last 30 days)

- 2026-05-04: Built full Python analysis pipeline — db.py + 5 analysis modules + main.py
- 2026-05-04: Defined disjoint COVID periods in `periods.py` (was overlapping in original H0 formulation)
- 2026-05-04: Smoke-tested all 5 analyses with synthetic data — all pass

## Active work

- [ ] Run `main.py --refresh` against real DB and inspect outputs
- [ ] Fill in Chapter 4 of `desk.docx` based on real ANOVA + changepoint results
- [ ] Add Cramér's V interpretation to chi-square report (currently 0,047 on synthetic data — need to see real value)
- [ ] Decide whether to add a regression model (linear or Poisson) for trend strength — currently NOT in scope, see Open questions

## Open questions for the supervisor

- Is the snowball sampling acceptable for inference, or do we need to weaken claims to "this sample" rather than "Czech Steam users"?
- Should the report acknowledge the achievement-spam game limitation in the methodology chapter, or just in the discussion?
- Are R figures + Python tables OK, or should everything be in the same tool?

## Known issues / weird stuff (don't try to "fix")

- **Daily activity has zero-count days.** Intentional — `db.py` uses `generate_series` to keep the time series complete. STL would break otherwise.
- **Median of `total_games_owned` is 0.** Real, not a bug. ~half the user base never bought a paid game (free-to-play accounts). Documented in Chapter 2.
- **CS:GO → CS2 transition (Sept 2023).** Achievement system changed; Q4 2023 data is partially affected. Already noted in the thesis.
- **`drafts/desk.docx` has the original DB password in it.** Already flagged in CLAUDE.md security section.

## Session handoff

When ending a session, update:
- "Recently done" — add what got finished today
- "Active work" — check off what's done, add what's new
- The top "Where we are" sentence if the situation shifted significantly

When starting a session: read this file first, then ask Claude to continue from "Active work".
