# reflections

Tracking maintenance and community adoption of pyOpenSci-accepted packages.

The first supported analysis measures how long pull requests wait for an
initial maintainer response before and after a package's pyOpenSci acceptance.
The `6/pyOS-approved` label on a closed issue in
`PyOpenSci/software-submission` is the authoritative acceptance signal.

## Set up the project

Install the locked development environment:

```console
uv sync
```

For live collection, create a `.env` file containing a GitHub token:

```dotenv
GITHUB_TOKEN=your-token
```

The token is optional for public data, but anonymous GitHub API requests have
a much lower rate limit. `.env` files are ignored by Git.

## Collect and analyze data

The public interface separates live GitHub collection from analysis:

```python
from reflections import (
    calculate_first_response_times,
    collect_repository_snapshot,
    get_submission,
    load_snapshot,
    save_snapshot,
)

submission = get_submission("swiftgalaxy")
snapshot = collect_repository_snapshot(
    submission.repository,
    accepted_at=submission.accepted_at,
)
save_snapshot(snapshot, "data/github/swiftgalaxy.json")

response_times = calculate_first_response_times(snapshot)

# Reproduce the analysis later without making GitHub requests.
saved_snapshot = load_snapshot("data/github/swiftgalaxy.json")
saved_response_times = calculate_first_response_times(saved_snapshot)
```

Snapshots are readable, schema-versioned JSON. They record the repository,
acceptance time, collection time, pull requests, and response events needed by
the metric. Commit deliberately selected snapshots when an analysis must be
reproduced without relying on GitHub's current state.

By default, a maintainer response is activity from a GitHub user associated as
an `OWNER`, `MEMBER`, or `COLLABORATOR`. Conversation comments, inline review
comments, and submitted reviews—including reviews without text—are included.
Bot activity, the pull-request author's own activity, and activity after PR
closure are excluded. These choices can be changed with
`MaintainerResponsePolicy`.

## Test

The test suite uses fixed local objects and does not make GitHub API requests:

```console
uv run python -m unittest discover -s tests -v
```
