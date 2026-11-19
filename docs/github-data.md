# GitHub data workflows

The GitHub data source maintains independent snapshots for pull-request
responses and commit activity. Collecting one does not invalidate or repeat
the other.

## Pull-request responses

```console
uv run python scripts/collect_accepted_packages.py
uv run python scripts/build_pr_dataset.py
uv run python scripts/build_figures.py
```

Pull-request snapshots are stored in `data/github/`. The derived table is
`data/derived/pull_requests.csv`. It includes first-response time, time to
close, time to merge, outcome, and censoring fields. Open PRs are retained:
their `observed_open_days` runs through the snapshot date and
`resolution_censored` is true. The median-close figure is explicitly limited
to closed PRs; use the censoring fields for survival analyses that compare all
PRs.

## Commit activity

```console
uv run python scripts/collect_commit_activity.py
uv run python scripts/build_commit_dataset.py
uv run python scripts/build_commit_figures.py
```

Commit snapshots are stored in `data/github/commits/`. The derived table is
`data/derived/commits.csv` and contains one row per commit.

The initial commit policy is:

- commits reachable from the repository's default branch;
- a matched 365-day window before and after pyOpenSci acceptance;
- committer time determines the before/after period;
- author time and committer time are both retained;
- merge commits and bot commits are retained and identified; and
- commit messages are retained, but email addresses are not.

Figure generation writes `figures/commits/commit_summary.csv` plus coverage,
before/after count, and relative monthly activity plots. Merge and bot commits
can be excluded without recollecting data:

```console
uv run python scripts/build_commit_figures.py --exclude-merges --exclude-bots
```

Both collectors show API quota and progress. Partial snapshots are safe to
resume after interruption or rate limiting. Use `--refresh` only when an
existing completed snapshot should be replaced.
