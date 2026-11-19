"""Tools for reflecting on pyOpenSci package maintenance and adoption."""

from .datasources.github import (
    collect_repository_snapshot,
    get_accepted_submissions,
    get_submission,
    load_snapshot,
    save_snapshot,
)
from .metrics import MaintainerResponsePolicy, calculate_first_response_times

__all__ = [
    "MaintainerResponsePolicy",
    "calculate_first_response_times",
    "collect_repository_snapshot",
    "get_accepted_submissions",
    "get_submission",
    "load_snapshot",
    "save_snapshot",
]


def main() -> None:
    print("See the reflections README for library and notebook usage.")
