"""Project CLI and shared command-line helpers."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def github_token(dotenv_path: Path = Path(".env")) -> str | None:
    """Read GitHub credentials without exposing or broadly loading .env."""

    token = os.getenv("GITHUB_TOKEN") or os.getenv("github_pat")
    if token or not dotenv_path.exists():
        return token

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        if key.strip() in {"GITHUB_TOKEN", "github_pat"}:
            return value.strip().strip("'\"") or None
    return None


class ProgressBar:
    """A dependency-free terminal progress bar for collection scripts."""

    width = 24

    def __init__(self, label: str, *, item_name: str):
        self.label = label
        self.item_name = item_name
        self.started_at = time.monotonic()
        self._last_non_terminal_update = 0

    def update(
        self,
        current: int,
        total: int,
        *,
        item_identifier: str | int,
        cached: bool,
        remaining: int,
    ) -> None:
        if not sys.stdout.isatty():
            interval = max(1, total // 20)
            if current != total and current - self._last_non_terminal_update < interval:
                return
            self._last_non_terminal_update = current
            print(
                f"{self.label}: {self.item_name} {current}/{total} "
                f"({item_identifier}, quota {remaining:,})"
                + (" [cached]" if cached else ""),
                flush=True,
            )
            return

        fraction = current / total if total else 1
        filled = round(self.width * fraction)
        bar = "#" * filled + "-" * (self.width - filled)
        elapsed = format_elapsed(time.monotonic() - self.started_at)
        cached_note = " cached" if cached else ""
        print(
            f"\r{self.label} [{bar}] {current}/{total} "
            f"{self.item_name} {item_identifier}{cached_note} | {elapsed} | "
            f"quota {remaining:,}",
            end="",
            flush=True,
        )

    def finish(self, item_count: int) -> None:
        self.finish_message(f"saved {item_count} {self.item_name.lower()}s")

    def finish_message(self, message: str) -> None:
        if sys.stdout.isatty():
            print()
        elapsed = format_elapsed(time.monotonic() - self.started_at)
        print(f"{self.label}: {message} in {elapsed}", flush=True)


def format_elapsed(seconds: float) -> str:
    minutes, whole_seconds = divmod(round(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{whole_seconds:02d}"
    return f"{minutes:02d}:{whole_seconds:02d}"


def main(argv: list[str] | None = None) -> int:
    """Run the project-level collection and analysis command."""

    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "status":
        return _status(args)
    if args.command == "collect":
        return _collect(args)
    if args.command == "analyze":
        return _analyze(args)
    parser.print_help()
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reflections",
        description="Collect and analyze pyOpenSci package histories.",
    )
    commands = parser.add_subparsers(dest="command")

    status = commands.add_parser("status", help="summarize local collection state")
    status.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    status.add_argument(
        "--indexes", type=Path, default=Path("data/github/history_indexes")
    )
    status.add_argument(
        "--interactions", type=Path, default=Path("data/github/interactions")
    )

    collect = commands.add_parser("collect", help="resume GitHub collection")
    collect.add_argument(
        "target",
        choices=("cohort", "commits", "comments", "indexes", "maintainers", "stars"),
    )
    collect.add_argument("--cohort", type=Path, default=Path("data/derived/cohort.csv"))
    collect.add_argument("--request-budget", type=int, default=100)
    collect.add_argument("--quota-floor", type=int, default=1000)
    collect.add_argument("--retry-failures", action="store_true")
    collect.add_argument("--refresh", action="store_true")
    collect.add_argument("--limit", type=int)
    collect.add_argument("--window-days", type=int)
    collect.add_argument("--minimum-post-acceptance-days", type=int)
    collect.add_argument("--check-auth", action="store_true")
    collect.add_argument("--output", type=Path)
    collect.add_argument("--roster", type=Path)
    collect.add_argument(
        "--entity",
        help="one entity type instead of both supported types",
    )

    analyze = commands.add_parser("analyze", help="rebuild local GitHub analyses")
    analyze.add_argument(
        "target", choices=("all", "cohort", "commits", "github", "maintainers", "stars")
    )
    analyze.add_argument("--windows", type=int, nargs="+", default=(90, 180, 365))
    analyze.add_argument("--response-horizon", type=int, default=30)
    analyze.add_argument("--exclude-merges", action="store_true")
    analyze.add_argument("--exclude-bots", action="store_true")
    analyze.add_argument(
        "--dry-run",
        action="store_true",
        help="print the reproducible commands without running them",
    )
    return parser


def _status(args) -> int:
    from reflections.analysis.history_index_manifest import history_index_manifest
    from reflections.analysis.interaction_manifest import interaction_manifest
    from reflections.workflows import read_repositories

    try:
        repositories = read_repositories(args.cohort)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Cohort: {len(repositories)} GitHub repositories")
    _print_status(
        "Tier 1 indexes",
        history_index_manifest(repositories, args.indexes),
        "entity_type",
    )
    _print_status(
        "Tier 2 comments",
        interaction_manifest(repositories, args.interactions),
        "interaction_type",
    )
    return 0


def _print_status(label, manifest, entity_column):
    print(f"{label}:")
    counts = (
        manifest.groupby([entity_column, "status"], sort=True)
        .size()
        .to_dict()
    )
    for (entity, status), count in counts.items():
        print(f"  {entity}: {status}={count}")


def _collect(args) -> int:
    if args.target not in {"indexes", "comments"}:
        return subprocess.run(collection_command(args), check=False).returncode

    from reflections.analysis.history_index_manifest import (
        write_history_index_manifest,
    )
    from reflections.analysis.interaction_manifest import write_interaction_manifest
    from reflections.datasources.github import (
        collect_history_index,
        collect_interaction_stream,
        create_github,
        load_history_index,
        load_interaction_snapshot,
        save_history_index,
        save_interaction_snapshot,
    )
    from reflections.workflows import read_repositories, run_cohort_collection

    if args.request_budget <= 0:
        raise SystemExit("--request-budget must be positive")
    if args.quota_floor < 0:
        raise SystemExit("--quota-floor must not be negative")
    try:
        repositories = read_repositories(args.cohort)
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    if args.target == "indexes":
        supported = ("issues", "pull_requests")
        output = Path("data/github/history_indexes")
        manifest = Path("data/derived/history_index_manifest.csv")
        components = (
            collect_history_index,
            load_history_index,
            save_history_index,
            write_history_index_manifest,
            "entity_type",
        )
    else:
        supported = ("issue_comments", "review_comments")
        output = Path("data/github/interactions")
        manifest = Path("data/derived/interaction_manifest.csv")
        components = (
            collect_interaction_stream,
            load_interaction_snapshot,
            save_interaction_snapshot,
            write_interaction_manifest,
            "interaction_type",
        )
    entities = _selected_entities(args.entity, supported)
    collector, loader, saver, manifest_writer, error_field = components
    return run_cohort_collection(
        repositories,
        entities,
        client=create_github(token=github_token()),
        output=output,
        manifest=manifest,
        request_budget=args.request_budget,
        quota_floor=args.quota_floor,
        retry_failures=args.retry_failures,
        collector=collector,
        loader=loader,
        saver=saver,
        manifest_writer=manifest_writer,
        error_entity_field=error_field,
    )


def _selected_entities(requested, supported):
    if requested is None or requested == "both":
        return supported
    if requested not in supported:
        choices = ", ".join((*supported, "both"))
        raise SystemExit(f"--entity must be one of: {choices}")
    return (requested,)


def _analyze(args) -> int:
    if any(window <= 0 for window in args.windows):
        raise SystemExit("--windows must contain positive integers")
    if args.response_horizon <= 0:
        raise SystemExit("--response-horizon must be positive")
    commands = analysis_commands(args)
    for command in commands:
        print(" ".join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, check=True)
    return 0


def collection_command(args) -> tuple[str, ...]:
    """Return the private command for a non-Tier collection target."""

    modules = {
        "cohort": "collect_cohort_metadata",
        "commits": "collect_commit_activity",
        "maintainers": "collect_maintainer_activity",
        "stars": "collect_star_history",
    }
    command = [sys.executable, "-m", f"reflections.commands.{modules[args.target]}"]
    for option in ("output", "roster", "limit", "window_days", "minimum_post_acceptance_days"):
        value = getattr(args, option)
        if value is not None:
            command.extend((f"--{option.replace('_', '-')}", str(value)))
    for flag in ("refresh", "check_auth"):
        if getattr(args, flag):
            command.append(f"--{flag.replace('_', '-')}")
    return tuple(command)


def analysis_commands(args) -> tuple[tuple[str, ...], ...]:
    """Return the local build sequence for an analysis target."""

    python = sys.executable
    domain_commands = {
        "cohort": (
            (python, "-m", "reflections.commands.build_cohort_dataset"),
            (python, "-m", "reflections.commands.build_cohort_figures"),
        ),
        "commits": (
            (python, "-m", "reflections.commands.build_commit_dataset"),
            (
                python,
                "-m",
                "reflections.commands.build_commit_figures",
                *(() if not args.exclude_merges else ("--exclude-merges",)),
                *(() if not args.exclude_bots else ("--exclude-bots",)),
            ),
        ),
        "maintainers": (
            (python, "-m", "reflections.commands.build_maintainer_dataset"),
            (python, "-m", "reflections.commands.build_maintainer_figures"),
        ),
        "stars": (
            (python, "-m", "reflections.commands.build_star_dataset"),
            (python, "-m", "reflections.commands.build_star_figures"),
        ),
    }
    github = github_analysis_commands(
        args.windows,
        response_horizon=args.response_horizon,
    )
    if args.target == "github":
        return github
    if args.target == "all":
        return tuple(
            command
            for target in ("cohort", "commits", "stars", "maintainers")
            for command in domain_commands[target]
        ) + github
    return domain_commands[args.target]


def github_analysis_commands(
    windows: list[int] | tuple[int, ...],
    *,
    response_horizon: int = 30,
) -> tuple[tuple[str, ...], ...]:
    """Return the complete deterministic local-analysis command sequence."""

    python = sys.executable
    commands: list[tuple[str, ...]] = []
    for window in windows:
        tier1_data = Path(f"data/derived/tier1/{window}_days")
        tier2_data = Path(f"data/derived/tier2/{window}_days")
        commands.extend(
            [
                (
                    python,
                    "-m",
                    "reflections.commands.build_tier1_datasets",
                    "--window-days",
                    str(window),
                    "--issue-output",
                    str(tier1_data / "issues.csv"),
                    "--pr-output",
                    str(tier1_data / "pull_requests.csv"),
                ),
                (
                    python,
                    "-m",
                    "reflections.commands.build_tier1_figures",
                    "--issues",
                    str(tier1_data / "issues.csv"),
                    "--pull-requests",
                    str(tier1_data / "pull_requests.csv"),
                    "--cohort-output",
                    f"figures/cohort/tier1_{window}_days",
                    "--issue-output",
                    f"figures/issues/tier1_{window}_days",
                    "--pr-output",
                    f"figures/pull_requests/tier1_{window}_days",
                ),
                (
                    python,
                    "-m",
                    "reflections.commands.build_tier2_datasets",
                    "--window-days",
                    str(window),
                    "--issue-output",
                    str(tier2_data / "issues.csv"),
                    "--pr-output",
                    str(tier2_data / "pull_requests.csv"),
                    "--coverage-output",
                    str(tier2_data / "coverage.csv"),
                ),
                (
                    python,
                    "-m",
                    "reflections.commands.build_tier2_figures",
                    "--issues",
                    str(tier2_data / "issues.csv"),
                    "--pull-requests",
                    str(tier2_data / "pull_requests.csv"),
                    "--coverage",
                    str(tier2_data / "coverage.csv"),
                    "--cohort-output",
                    f"figures/cohort/tier2_{window}_days",
                    "--issue-output",
                    f"figures/issues/tier2_{window}_days",
                    "--pr-output",
                    f"figures/pull_requests/tier2_{window}_days",
                    "--response-horizon",
                    str(response_horizon),
                ),
            ]
        )
    commands.extend(
        [
            (
                python,
                "-m",
                "reflections.commands.build_tier1_window_summary",
                "--windows",
                *(str(window) for window in windows),
            ),
            (
                python,
                "-m",
                "reflections.commands.build_tier2_window_summary",
                "--windows",
                *(str(window) for window in windows),
                "--response-horizon",
                str(response_horizon),
            ),
        ]
    )
    return tuple(commands)
