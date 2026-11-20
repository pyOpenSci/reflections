# GitHub data workflows

The GitHub data source maintains independent snapshots for pull-request
responses, commit activity, and issue timelines. Collecting one does not
invalidate or repeat the others.

## Cohort metadata

```console
uv run python scripts/collect_cohort_metadata.py
uv run python scripts/build_cohort_dataset.py
uv run python scripts/build_cohort_figures.py
```

The cohort collector reads the cached accepted-package roster and stores one
small snapshot per GitHub-hosted package in `data/github/cohort/`. The derived
`data/derived/cohort.csv` contains submission and acceptance dates, review
duration, repository creation date, listed-maintainer count, and the latest
default-branch commit timestamp. Collection is resumable and existing
snapshots are reused unless `--refresh` is supplied. The cohort figure builder
writes presentation-ready profile figures to `figures/cohort/`.

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

## Issue response and resolution

```console
uv run python scripts/collect_issue_activity.py
uv run python scripts/build_issue_dataset.py
uv run python scripts/build_issue_figures.py
```

Issue snapshots are stored in `data/github/issues/`; pull requests returned by
GitHub's Issues API are excluded. The derived `data/derived/issues.csv` keeps
separate times for the first maintainer acknowledgement, first triage action,
first of either ("addressed"), and closure. Acknowledgement means a comment by
an owner, member, or collaborator. Triage means a label, assignment, milestone,
or closure action by someone other than the issue author or a bot. Open and
unaddressed issues remain in the table with censoring fields.

## Star history

```console
uv run python scripts/collect_star_history.py
uv run python scripts/build_star_dataset.py
uv run python scripts/build_star_figures.py
```

Aggregate star snapshots are stored in `data/github/stars/`. Collection uses
GitHub's repository star-history endpoint and does not store stargazer
identities. `data/derived/stars.csv` expands the weekly response to one row per
day with new and cumulative star acquisitions. The current star count is also
retained because historical acquisitions can differ from the current count
when users remove stars. Collection checkpoints every API page and is safe to
resume.

## Maintainer activity

```console
uv run python scripts/collect_maintainer_activity.py
uv run python scripts/build_maintainer_dataset.py
uv run python scripts/build_maintainer_figures.py
```

The authoritative review-time roster comes from `All current maintainers` in
each accepted submission issue. Each unique GitHub account is queried once for
the most recent fixed 365-day window. Snapshots live in
`data/github/maintainers/users/`, while `roster.json` preserves the package
mapping and observation dates so interrupted runs remain reproducible.

The activity table reports public commits, opened issues, opened pull requests,
and pull-request reviews. It also reports the share associated with the
accepted package. GitHub only returns repository breakdowns for up to 100
repositories per contribution type; affected package counts are marked unknown
and retain a lower bound rather than being recorded as zero. Restricted/private
contribution counts are retained as a visibility warning and are not treated as
package inactivity.

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
- snapshots retain a matched 365-day window before and after acceptance;
- the default analysis compares 90 days before with 90 days after acceptance;
- packages enter that analysis only after 90 post-acceptance days have been
  observed;
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
