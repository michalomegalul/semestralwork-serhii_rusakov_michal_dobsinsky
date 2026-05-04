# Rules for analysis_*.py modules

These rules apply when working in `analysis_*.py` files specifically.

## Standard module shape

Every analysis module MUST:

1. Have a top-level docstring in Czech explaining: hypothesis, method, output files
2. Import data via `db.load(name)` — never connect to DB directly
3. Define one `run()` function as the entry point
4. Have a `if __name__ == "__main__": run()` block at the bottom
5. Write a `.txt` report (lidsky čitelný) AND a `.png` graph to `outputs/`
6. Be runnable standalone (so we can iterate on one method without running all five)

## Statistical reporting

When writing report text inside the modules:

- Header: `=` * 70, name in CAPS, blank line
- Hypotheses: state H0 and H1 explicitly, both in Czech
- Significance level: always state α = 0,05 explicitly (don't assume reader knows)
- Numbers: 4 significant digits for p-values (`{p:.4g}`), 2 decimals for test statistics
- Verdicts: "ZAMÍTÁME" / "NEZAMÍTÁME" — supervisor wants the explicit decision in writing
- Always include effect size, not just p

## Plot conventions

- `figsize=(10, 6)` for single panels, `(15, 5)` for 1x3 grids, `(14, 10)` for STL 4-panel
- `dpi=150` on save (sharp in Word at 150% zoom)
- Czech labels on axes and titles
- Use `alpha=0.3` on grids, never solid
- For period coloring use the palette: pre=#9ec5e8, covid=#e89e9e, post=#9ee8b8

## Anti-patterns

- DON'T plot in `run()` — keep plotting in private `_plot_*` helpers so the function is testable
- DON'T use `plt.show()` — we save to disk, not display
- DON'T forget `plt.close(fig)` after saving — matplotlib leaks memory in long sessions
- DON'T write CSV outputs from analysis modules — that's `db.py`'s job

## When the supervisor asks "why this method?"

Each analysis module's docstring should answer this in 2-3 sentences. If you can't justify the method choice, the wrong method was chosen. Examples already in the codebase:

- `analysis_anova.py`: "Skewed data → Kruskal-Wallis primary, ANOVA reference"
- `analysis_correlation.py`: "Spearman robust to outliers, Pearson assumes linearity"
- `analysis_changepoint.py`: "Monthly aggregates because daily series too noisy"
