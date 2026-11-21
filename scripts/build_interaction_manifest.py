"""Build the cohort-wide interaction collection manifest."""

import argparse
from pathlib import Path

from reflections.analysis.interaction_manifest import write_interaction_manifest
from reflections.workflows import read_repositories


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
    try:
        repositories = read_repositories(args.cohort)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    path = write_interaction_manifest(repositories, args.input, args.output)
    print(f"Wrote interaction manifest to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
