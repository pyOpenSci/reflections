# GitHub data workflows

The GitHub data source maintains independent snapshots for repository event
indexes, comment interactions, commits, stars, maintainers, and cohort
metadata. Collecting one does not invalidate or repeat the others. The Tier 1
event indexes and Tier 2 interaction streams are the authoritative issue and
pull-request workflow; see [full-history collection](full-history-collection.md)
for collection and rebuild commands.

## Cohort metadata

```console
uv run reflections collect cohort
uv run --extra analysis reflections analyze cohort
```

The cohort collector reads the cached accepted-package roster and stores one
small snapshot per GitHub-hosted package in `data/github/cohort/`. The derived
`data/derived/cohort.csv` contains submission and acceptance dates, review
duration, repository creation date, listed-maintainer count, and the latest
default-branch commit timestamp. Collection is resumable and existing
snapshots are reused unless `--refresh` is supplied. The cohort figure builder
writes presentation-ready profile figures to `figures/cohort/`.

## Issues and pull requests

Tier 1 stores complete lightweight issue and pull-request indexes in
`data/github/history_indexes/`. Tier 2 stores repository-wide conversation and
inline review comments in `data/github/interactions/`. The derived tables retain
open and unanswered items with explicit censoring fields and can be rebuilt for
90-, 180-, or 365-day matched windows without querying GitHub again.

Formal reviews and issue timeline actions are not collected by the current
workflow. If the Tier 1 and Tier 2 results prove insufficient, Tier 3 should be
implemented from the analytic requirements rather than retaining the earlier
bounded prototype.

## Star history

```console
uv run reflections collect stars
uv run --extra analysis reflections analyze stars
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
uv run reflections collect maintainers
uv run --extra analysis reflections analyze maintainers
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
uv run reflections collect commits
uv run --extra analysis reflections analyze commits
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
uv run --extra analysis reflections analyze commits --exclude-merges --exclude-bots
```

Both collectors show API quota and progress. Partial snapshots are safe to
resume after interruption or rate limiting. Use `--refresh` only when an
existing completed snapshot should be replaced.
