# Full-history collection design

## Objective

Collect reusable repository histories without fixing an analysis window during
collection. Analysis tables can then choose symmetric 90-, 180-, or 365-day
windows without querying GitHub again.

“Full history” means the complete history needed for the planned metrics, not
every object exposed by GitHub. Raw collection and metric derivation remain
separate stages.

## Current request pattern

| Domain | Current source | Expensive operation | Cached scale |
| --- | --- | --- | ---: |
| Issues | REST issue list | One timeline request per issue | 4,737 issues |
| Pull requests | REST pull-request list | Issue comments, review comments, and reviews for every PR | 11,451 PRs |
| Commits | REST default-branch commits | Paginated commit objects | 36,870 commits |
| Stars | Aggregate star-history endpoint | Paginated weekly history | 744 pages |
| Maintainers | GraphQL contribution calendar | Per-maintainer contribution details | 125 cached users |

The cached files occupy approximately 57 MB. They cover bounded acceptance
windows for issues, pull requests, and commits, so these counts are lower
bounds for full history.

At the current scale, issue timelines alone require at least 4,737 requests.
Pull-request hydration requires at least three requests per PR—more than 34,000
requests before pagination of comments or reviews. Those two operations cannot
fit in a single authenticated 5,000-request quota window.

## Collection tiers

### Tier 1: complete event indexes

Collect lightweight, paginated records for all issues and pull requests:

- stable identifier and number;
- creation, update, close, and merge timestamps;
- author and state;
- repository and URL;
- comment and review counts when available.

This tier determines which objects are needed for any later analysis window.
It must complete before expensive per-item hydration begins.

### Tier 2: bulk interaction streams

Collect repository-wide issue comments and pull-request review comments where
GitHub provides bulk endpoints. Associate comments with their issue or pull
request locally. This avoids making an empty comments request for every item.

The issue-comment endpoint contains conversation comments from both issues and
pull requests. Each cached record therefore stores its parent number, and the
Tier 1 indexes determine whether that number belongs to an issue or a pull
request. Comment bodies are not retained. The cache includes only stable IDs,
parent numbers, interaction kind, author and association, timestamps, and URL.

Formal pull-request review submissions are not part of the bulk review-comment
stream and remain a Tier 3 collection.

### Tier 3: per-item details

Collect information that has no adequate bulk endpoint, including formal pull
request reviews and issue timeline events. This tier is page-checkpointed and
may run over several quota windows. Cached items are never requested again
unless an explicit refresh is requested.

### Commit history

Use filtered bare clones for public repositories instead of the GitHub API:

```bash
git clone --bare --filter=blob:none REPOSITORY_URL
```

The local commit graph supplies timestamps, author and committer identities,
merge-parent counts, and default-branch density without consuming API quota.
Repository metadata remains available from the small cohort snapshot.

### Stars and maintainers

The aggregate star-history snapshots are already unwindowed and resumable.
Maintainer activity remains a dated snapshot rather than a historical event
stream and should be refreshed as a separate operation.

## Snapshot and manifest requirements

Every raw collection unit should record:

- schema version and collection scope;
- repository and entity type;
- first and last observed event;
- fetched and last-updated timestamps;
- next page or item checkpoint;
- the complete GitHub continuation URL when pagination uses a cursor;
- source endpoint, including any documented fallback;
- collected and expected counts when known;
- completion state and failure message;
- core quota before and after collection.

The cohort manifest should distinguish `missing`, `partial`, `complete`, and
`stale` collection states. Atomic checkpoint writes ensure interruption does
not invalidate previously collected pages.

## Quota policy

Collectors should accept a request budget and protected quota floor. A run
stops cleanly before crossing either limit and reports the exact checkpoint
command needed to resume. The default policy should reserve at least 500 core
requests for normal project work.

Before each expensive tier, the collector should print:

- currently available quota;
- requested run budget;
- cached and remaining entities;
- a conservative minimum request estimate;
- whether completion is possible in the current quota window.

## Pilot and rollout

1. Implement the unwindowed issue and pull-request index schemas without
   changing the current snapshots.
2. Pilot index and bulk-comment collection on one medium repository with a
   strict request budget.
3. Validate resumability, deduplication, and request accounting.
4. Pilot a filtered bare clone and compare its derived 90-day commit counts
   with the existing API snapshot.
5. Run Tier 1 across the cohort.
6. Run interaction tiers incrementally, rebuilding the coverage audit after
   each quota window.

No cohort-wide full-history collection should begin until the pilot confirms
the request estimates and checkpoint behavior.

The bounded issue and pull-request index pilot can be run with:

```bash
uv run python scripts/collect_history_index.py OWNER/REPOSITORY \
  --entity both --request-budget 4 --quota-floor 500
```

The request budget is shared across both indexes. Each completed page is
written atomically, so rerunning the same command resumes at the next page.

After validating the pilot, cohort collection can proceed in bounded batches:

```bash
uv run python scripts/collect_cohort_history_indexes.py \
  --entity both --request-budget 100 --quota-floor 1000
```

The command reads the authoritative local cohort, skips completed indexes and
previously recorded repository-level failures, and writes
`data/derived/history_index_manifest.csv`. Use `--retry-failures` only after a
recorded repository or API problem has been investigated.

The collector follows GitHub's complete `rel="next"` URL rather than assuming
that every endpoint uses numbered pages. This supports both page-based and
cursor-based pagination and preserves the cursor in partial checkpoints. Old
version 1 checkpoints remain readable; a checkpoint at GitHub's 10,000-result
boundary re-reads its last successful page once to recover the cursor.

If the pull-request list endpoint returns 404 before yielding any records, the
collector falls back to the repository-issues endpoint and retains only items
marked as pull requests. The manifest records `issues` as the source endpoint.
Fields unavailable from that fallback, such as draft state and review-comment
count, remain null rather than being interpreted as false or zero.

The initial Tier 1 cohort run completed indexes for all 70 repositories: 20,058
issues and 40,251 pull requests. MovingPandas used the audited issues-endpoint
fallback and returned no historical pull-request records.

The bounded Tier 2 pilot can be run for one repository with:

```bash
uv run python scripts/collect_interaction_stream.py OWNER/REPOSITORY \
  --entity both --request-budget 10 --quota-floor 1000
```

The request budget is shared across issue comments and review comments. Every
page is written atomically, and rerunning the command resumes from GitHub's
stored continuation URL. Rebuild the cohort-level collection inventory with:

```bash
uv run python scripts/build_interaction_manifest.py
```

This writes `data/derived/interaction_manifest.csv`, with one row for each
repository and interaction type and an explicit `missing`, `partial`, or
`complete` state.

After validating the pilot, run cohort collection in bounded batches:

```bash
uv run python scripts/collect_cohort_interactions.py \
  --entity both --request-budget 100 --quota-floor 1000
```

Completed streams and recorded failures are skipped, while partial streams
resume from their stored continuation URL. Use `--retry-failures` only after
investigating the recorded API error.

Tier 1 comment counts indicate approximately 849 pages of issue and PR
conversation comments across the cohort. The PR list endpoint does not supply
inline review-comment counts, so the review-comment cost cannot be estimated
from Tier 1; its 70 one-page repository minimum is a lower bound rather than a
zero-comment estimate.
