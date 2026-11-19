"""Shared command-line helpers for collection scripts."""

import os
from pathlib import Path
import sys
import time


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
