"""Build the cohort-level CSV from cached metadata snapshots."""

import argparse
from pathlib import Path

from reflections import load_cohort_metadata, write_cohort_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", type=Path, default=Path("data/github/cohort"))
    parser.add_argument("--output", type=Path, default=Path("data/derived/cohort.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = sorted(args.snapshots.glob("*.json"))
    if not paths:
        raise SystemExit(f"No cohort metadata snapshots found in {args.snapshots}")
    output = write_cohort_csv(
        (load_cohort_metadata(path) for path in paths), args.output
    )
    print(f"Wrote {len(paths)} cohort rows to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
