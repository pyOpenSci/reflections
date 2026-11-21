import os
import unittest
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from reflections._cli import (
    ProgressBar,
    _parser,
    _selected_entities,
    analysis_commands,
    collection_command,
    github_analysis_commands,
    github_token,
)


class GitHubTokenTests(unittest.TestCase):
    def test_reads_token_from_dotenv(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('GITHUB_TOKEN="secret-token"\n', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                token = github_token(path)

        self.assertEqual(token, "secret-token")

    def test_environment_takes_precedence(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")
            with patch.dict(os.environ, {"GITHUB_TOKEN": "environment-token"}, clear=True):
                token = github_token(path)

        self.assertEqual(token, "environment-token")


class ProgressBarTests(unittest.TestCase):
    def test_non_terminal_progress_reports_counts_and_quota(self):
        output = StringIO()
        with patch("sys.stdout", output):
            progress = ProgressBar("[1/2] example/project", item_name="PR")
            progress.update(
                1,
                2,
                item_identifier="#10",
                cached=False,
                remaining=4_900,
            )

        message = output.getvalue()
        self.assertIn("PR 1/2", message)
        self.assertIn("#10", message)
        self.assertIn("quota 4,900", message)


class ProjectCommandTests(unittest.TestCase):
    def test_analysis_command_builds_every_window_and_both_summaries(self):
        commands = github_analysis_commands([90, 365], response_horizon=14)

        self.assertEqual(len(commands), 10)
        self.assertIn("data/derived/tier1/90_days/issues.csv", commands[0])
        self.assertIn("figures/cohort/tier2_365_days", commands[7])
        self.assertEqual(commands[-1][-1], "14")

    def test_collection_entity_selection_is_validated(self):
        supported = ("issues", "pull_requests")

        self.assertEqual(_selected_entities(None, supported), supported)
        self.assertEqual(_selected_entities("issues", supported), ("issues",))
        with self.assertRaisesRegex(SystemExit, "--entity must be one of"):
            _selected_entities("review_comments", supported)

    def test_non_tier_collection_uses_private_command(self):
        args = _parser().parse_args(
            ["collect", "commits", "--window-days", "365", "--limit", "2"]
        )

        command = collection_command(args)

        self.assertIn("reflections.commands.collect_commit_activity", command)
        self.assertEqual(command[-4:], ("--limit", "2", "--window-days", "365"))

    def test_all_analysis_includes_each_domain_and_tiers(self):
        args = _parser().parse_args(["analyze", "all", "--windows", "90"])

        commands = analysis_commands(args)

        modules = {command[2] for command in commands}
        self.assertIn("reflections.commands.build_cohort_dataset", modules)
        self.assertIn("reflections.commands.build_commit_dataset", modules)
        self.assertIn("reflections.commands.build_star_dataset", modules)
        self.assertIn("reflections.commands.build_maintainer_dataset", modules)
        self.assertIn("reflections.commands.build_tier2_figures", modules)


if __name__ == "__main__":
    unittest.main()
