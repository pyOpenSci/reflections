"""Tools for reflecting on pyOpenSci package maintenance and adoption."""

from .analysis import write_commit_csv, write_issue_csv, write_pull_request_csv
from .datasources.github import (
    collect_commit_snapshot,
    collect_issue_snapshot,
    collect_repository_snapshot,
    get_accepted_submissions,
    get_submission,
    load_commit_snapshot,
    load_issue_snapshot,
    load_snapshot,
    save_commit_snapshot,
    save_issue_snapshot,
    save_snapshot,
)
from .metrics import (
    IssueResponsePolicy,
    IssueTiming,
    MaintainerResponsePolicy,
    calculate_first_response_times,
    calculate_issue_times,
)

__all__ = [
    "MaintainerResponsePolicy",
    "IssueResponsePolicy",
    "IssueTiming",
    "calculate_first_response_times",
    "calculate_issue_times",
    "collect_commit_snapshot",
    "collect_issue_snapshot",
    "collect_repository_snapshot",
    "get_accepted_submissions",
    "get_submission",
    "load_commit_snapshot",
    "load_issue_snapshot",
    "load_snapshot",
    "save_commit_snapshot",
    "save_issue_snapshot",
    "save_snapshot",
    "write_pull_request_csv",
    "write_commit_csv",
    "write_issue_csv",
]


def main() -> None:
    print("See the reflections README for library and notebook usage.")
