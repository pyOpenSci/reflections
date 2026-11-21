"""Internal maintainer dataset build command."""

import argparse
import sys
from pathlib import Path

from reflections.analysis.maintainer_tables import write_maintainer_csvs
from reflections.datasources.github import (
    load_maintainer_activity,
    load_maintainer_roster,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, default=Path("data/github/maintainers"))
    parser.add_argument(
        "--activity-output", type=Path,
        default=Path("data/derived/maintainer_activity.csv"),
    )
    parser.add_argument(
        "--roster-output", type=Path,
        default=Path("data/derived/maintainer_rosters.csv"),
    )
    args = parser.parse_args()
    submissions, _, _, _ = load_maintainer_roster(args.snapshots / "roster.json")
    paths = sorted((args.snapshots / "users").glob("*.json"))
    if not paths:
        raise SystemExit("No maintainer activity snapshots found")
    snapshots = [load_maintainer_activity(path) for path in paths]
    available = {item.requested_login.casefold() for item in snapshots}
    missing = sorted(
        {
            login
            for submission in submissions
            for login in submission.maintainers
            if login.casefold() not in available
        },
        key=str.casefold,
    )
    if missing:
        print(
            f"Warning: {len(missing)} maintainer snapshot(s) unavailable: "
            + ", ".join(f"@{login}" for login in missing),
            file=sys.stderr,
        )
    outputs = write_maintainer_csvs(
        submissions, snapshots,
        activity_path=args.activity_output, roster_path=args.roster_output,
    )
    print(f"Wrote {outputs[0]} and {outputs[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
