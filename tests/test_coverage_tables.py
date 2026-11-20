import json

import pandas as pd

from reflections.analysis.coverage_tables import build_coverage_tables


def test_build_coverage_tables_distinguishes_missing_and_partial(tmp_path):
    derived = tmp_path / "derived"
    derived.mkdir()
    cohort = pd.DataFrame(
        {
            "repository": ["org/one", "org/two"],
            "accepted_at": ["2020-01-01T00:00:00+00:00"] * 2,
            "snapshot_fetched_at": ["2022-01-01T00:00:00+00:00"] * 2,
        }
    )
    cohort_path = derived / "cohort.csv"
    cohort.to_csv(cohort_path, index=False)

    for directory, event_key in (
        ("github", "pull_requests"),
        ("github/issues", "issues"),
        ("github/commits", "commits"),
        ("github/stars", "weeks"),
    ):
        path = tmp_path / directory
        path.mkdir(parents=True, exist_ok=True)
        payload = {
            "repository": "org/one",
            "fetched_at": "2022-01-01T00:00:00+00:00",
            "window_days": 365,
            event_key: [{}],
        }
        if event_key == "weeks":
            payload["complete"] = True
        (path / "org--one.json").write_text(json.dumps(payload))

    for filename in ("pull_requests.csv", "issues.csv", "commits.csv", "stars.csv"):
        pd.DataFrame(
            {"repository": ["org/one"], "within_window": [True]}
        ).to_csv(derived / filename, index=False)

    pd.DataFrame(
        {
            "repository": ["org/one", "org/two"],
            "has_maintainer_roster": [True, True],
        }
    ).to_csv(derived / "maintainer_rosters.csv", index=False)
    pd.DataFrame(
        {
            "repository": ["org/one", "org/two"],
            "snapshot_available": [True, False],
        }
    ).to_csv(derived / "maintainer_activity.csv", index=False)

    summary, detail = build_coverage_tables(cohort_path, tmp_path)

    pull_requests = summary.set_index("metric").loc["pull_requests"]
    assert pull_requests["complete_snapshots"] == 1
    assert pull_requests["missing_snapshots"] == 1
    assert pull_requests["analysis_repositories"] == 1
    maintainer_two = detail.loc[
        (detail["metric"] == "maintainers")
        & (detail["repository"] == "org/two")
    ].iloc[0]
    assert maintainer_two["snapshot_status"] == "partial"
    assert maintainer_two["exclusion_reason"] == "partial_snapshot"
