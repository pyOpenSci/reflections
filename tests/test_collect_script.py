import os
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
import unittest
from unittest.mock import patch

from reflections._cli import ProgressBar, github_token


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


if __name__ == "__main__":
    unittest.main()
