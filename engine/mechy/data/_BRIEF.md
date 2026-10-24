# Brief for engineering-data agents

Mechy's LLM agents (see engine/mechy/prompts/_standards.md) need machine-readable lookup data so they
use real numbers instead of guesses. You build one dataset folder of CSV/JSON files.

Rules:
1. Each CSV has a header row, SI units in column names (e.g. yield_strength_MPa, mass_kg), one row per
   item, and `source_url` + `value_type` (datasheet | standard | handbook_typical | estimate) columns.
   Cross-check key numbers against two sources where possible.
2. Prefer compiling from public, reputable sources: standards summaries, government/NIST/NASA data,
   manufacturer datasheets, university notes, Wikipedia tables with references. Respect licences:
   do NOT scrape or bulk-copy sites whose terms forbid it (e.g. MatWeb, paywalled handbooks); summarise
   typical values with citations instead.
3. You may download raw data files only from reputable sources (government, standards bodies,
   manufacturers, well-known GitHub projects) with a licence allowing reuse, into <your folder>/raw/.
   Never run or execute downloaded files. Keep your folder under 20 MB total.
4. Write <your folder>/README.md: what each file contains, row count, columns, sources and licences,
   and "Gaps / not verified".
5. Write a small validator <your folder>/check.py (Python stdlib only) that loads every CSV/JSON, checks
   required columns, units sanity (no negative densities, yield <= UTS, etc.) and prints PASS/FAIL.
   Run it with `python3 -I check.py` and make it pass.
6. Only write inside your folder. Do not commit. Reply with a 5-line summary incl. row counts.
