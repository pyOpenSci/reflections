"""Tools for reflecting on pyOpenSci package maintenance and adoption."""

from .datasources.github import get_accepted_submissions, get_submission

__all__ = ["get_accepted_submissions", "get_submission"]


def main() -> None:
    from ._cli import main as cli_main

    raise SystemExit(cli_main())
