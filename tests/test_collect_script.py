import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
import unittest
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "collect_accepted_packages.py"
SPEC = importlib.util.spec_from_file_location("collect_accepted_packages", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
COLLECT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(COLLECT)


class GitHubTokenTests(unittest.TestCase):
    def test_reads_token_from_dotenv(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('GITHUB_TOKEN="secret-token"\n', encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                token = COLLECT._github_token(path)

        self.assertEqual(token, "secret-token")

    def test_environment_takes_precedence(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("GITHUB_TOKEN=file-token\n", encoding="utf-8")
            with patch.dict(os.environ, {"GITHUB_TOKEN": "environment-token"}, clear=True):
                token = COLLECT._github_token(path)

        self.assertEqual(token, "environment-token")


class ProgressBarTests(unittest.TestCase):
    def test_non_terminal_progress_reports_counts_and_quota(self):
        output = StringIO()
        with patch("sys.stdout", output):
            progress = COLLECT.ProgressBar("[1/2] example/project")
            progress.update(
                1,
                2,
                pull_request_number=10,
                cached=False,
                remaining=4_900,
            )

        message = output.getvalue()
        self.assertIn("PR 1/2", message)
        self.assertIn("#10", message)
        self.assertIn("quota 4,900", message)


if __name__ == "__main__":
    unittest.main()
