# Data coverage audit

This report is generated from the local cohort, snapshots, and derived tables.
Regenerate it with `uv run python scripts/build_coverage_audit.py` after rebuilding the derived datasets.

| Metric | Cohort | Eligible | Complete | Partial | Missing | Included |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Commits | 70 | 64 | 67 | 1 | 2 | 59 |
| Issues | 70 | 70 | 70 | 0 | 0 | 68 |
| Maintainers | 70 | 68 | 67 | 1 | 2 | 67 |
| Pull Requests | 70 | 70 | 66 | 1 | 3 | 65 |
| Stars | 70 | 70 | 70 | 0 | 0 | 70 |

‘Included’ means that a repository is eligible, has usable local data, and contributes at least one observation to the current analysis table.

## Exclusions requiring attention

- `HzaCode/ChemInformant` — commits: missing snapshot
- `astropy/astropy` — commits: partial snapshot
- `lintquarto/lintquarto` — commits: missing snapshot
- `astropy/astropy` — maintainers: partial snapshot
- `HzaCode/ChemInformant` — pull requests: missing snapshot
- `astropy/astropy` — pull requests: partial snapshot
- `lintquarto/lintquarto` — pull requests: missing snapshot
- `movingpandas/movingpandas` — pull requests: missing snapshot

## Other exclusions

Repositories marked `not_eligible` do not satisfy a metric-specific follow-up or data requirement. Repositories marked `no_events_in_analysis_window` have a usable snapshot but no events in the current analysis window. Full details are available in `data/derived/coverage_details.csv`.
