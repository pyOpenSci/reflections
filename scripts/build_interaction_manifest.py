"""Build the cohort-wide interaction collection manifest."""

import argparse
import csv
from pathlib import Path

from reflections.analysis.interaction_manifest import write_interaction_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/github/interactions"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/derived/interaction_manifest.csv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.cohort.open(newline="", encoding="utf-8") as stream:
        repositories = [row["repository"] for row in csv.DictReader(stream)]
    if not repositories:
        raise SystemExit(f"No repositories found in {args.cohort}")
    path = write_interaction_manifest(repositories, args.input, args.output)
    print(f"Wrote interaction manifest to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
