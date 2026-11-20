"""Build data coverage and exclusion audit tables from local files."""

import argparse
from pathlib import Path

from reflections.analysis.coverage_tables import (
    build_coverage_tables,
    write_coverage_report,
    write_coverage_tables,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("data/derived"))
    parser.add_argument("--report", type=Path, default=Path("docs/data-coverage.md"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary, detail = build_coverage_tables(args.cohort, args.data)
    summary_path, detail_path = write_coverage_tables(
        args.cohort, args.data, args.output
    )
    report_path = write_coverage_report(summary, detail, args.report)
    print(f"Wrote {summary_path}, {detail_path}, and {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
