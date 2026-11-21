"""Tools for reflecting on pyOpenSci package maintenance and adoption."""

from .analysis import (
    CommentResponsePolicy,
    write_cohort_csv,
    write_comment_response_csv,
    write_commit_csv,
    write_maintainer_csvs,
    write_star_csv,
    write_tier1_issue_csv,
    write_tier1_pull_request_csv,
)
from .datasources.github import (
    collect_cohort_metadata,
    collect_commit_snapshot,
    collect_history_index,
    collect_interaction_stream,
    collect_maintainer_activity,
    collect_star_snapshot,
    get_accepted_submissions,
    get_submission,
    load_cohort_metadata,
    load_commit_snapshot,
    load_history_index,
    load_interaction_snapshot,
    load_maintainer_activity,
    load_maintainer_roster,
    load_star_snapshot,
    save_cohort_metadata,
    save_commit_snapshot,
    save_history_index,
    save_interaction_snapshot,
    save_maintainer_activity,
    save_maintainer_roster,
    save_star_snapshot,
)

__all__ = [
    "CommentResponsePolicy",
    "collect_cohort_metadata",
    "collect_commit_snapshot",
    "collect_history_index",
    "collect_interaction_stream",
    "collect_maintainer_activity",
    "collect_star_snapshot",
    "get_accepted_submissions",
    "get_submission",
    "load_cohort_metadata",
    "load_commit_snapshot",
    "load_history_index",
    "load_interaction_snapshot",
    "load_maintainer_activity",
    "load_maintainer_roster",
    "load_star_snapshot",
    "save_cohort_metadata",
    "save_commit_snapshot",
    "save_history_index",
    "save_interaction_snapshot",
    "save_maintainer_activity",
    "save_maintainer_roster",
    "save_star_snapshot",
    "write_cohort_csv",
    "write_comment_response_csv",
    "write_commit_csv",
    "write_maintainer_csvs",
    "write_star_csv",
    "write_tier1_issue_csv",
    "write_tier1_pull_request_csv",
]


def main() -> None:
    from ._cli import main as cli_main

    raise SystemExit(cli_main())
