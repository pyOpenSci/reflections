from datetime import UTC, datetime
import json

from reflections.analysis.history_index_manifest import history_index_manifest
from reflections.datasources.github import (
    collect_history_index,
    load_history_index,
    save_history_index,
)


class FakeGithub:
    def __init__(self, responses, remaining=1000):
        self.responses = iter(responses)
        self.rate_limiting = (remaining, 5000)
        self.requester = self

    def requestJsonAndCheck(self, method, url, parameters):
        assert method == "GET"
        assert url == "/repos/org/project/issues"
        assert parameters["per_page"] == 100
        return next(self.responses)


def issue(number):
    return {
        "number": number,
        "title": f"Issue {number}",
        "html_url": f"https://github.com/org/project/issues/{number}",
        "user": {"login": "person"},
        "created_at": f"2020-01-0{number}T00:00:00Z",
        "updated_at": f"2020-01-0{number}T01:00:00Z",
        "closed_at": None,
        "state": "open",
        "comments": 2,
    }


def test_history_index_resumes_by_page_and_round_trips(tmp_path):
    first_headers = {
        "link": '<https://api.github.com/x?page=2>; rel="next", '
        '<https://api.github.com/x?page=2>; rel="last"',
        "x-ratelimit-remaining": "998",
    }
    first = collect_history_index(
        "org/project",
        "issues",
        github=FakeGithub([(first_headers, [issue(1)])]),
        request_budget=1,
        quota_floor=500,
    )
    assert not first.complete
    assert first.next_page == 2
    assert first.requests_used == 1

    path = save_history_index(first, tmp_path / "issues.partial.json")
    checkpoint = load_history_index(path)
    second = collect_history_index(
        "org/project",
        "issues",
        github=FakeGithub([({"x-ratelimit-remaining": "997"}, [issue(2)])]),
        existing_snapshot=checkpoint,
        request_budget=1,
        quota_floor=500,
    )

    assert second.complete
    assert second.next_page == 3
    assert second.requests_used == 2
    assert [item.number for item in second.records] == [1, 2]


def test_history_index_manifest_includes_missing_and_complete(tmp_path):
    complete = collect_history_index(
        "org/project",
        "issues",
        github=FakeGithub([({}, [issue(1)])]),
        request_budget=1,
        quota_floor=500,
    )
    save_history_index(
        complete,
        tmp_path / "issues" / "org--project.json",
    )

    manifest = history_index_manifest(["org/project"], tmp_path)

    statuses = manifest.set_index("entity_type")["status"].to_dict()
    assert statuses == {"issues": "complete", "pull_requests": "missing"}


def test_history_index_manifest_records_failed_collection(tmp_path):
    error_path = tmp_path / "errors/pull_requests/org--project.json"
    error_path.parent.mkdir(parents=True)
    error_path.write_text(json.dumps({"message": "404 Not Found"}))

    manifest = history_index_manifest(["org/project"], tmp_path)
    pull_request = manifest.loc[
        manifest["entity_type"] == "pull_requests"
    ].iloc[0]

    assert pull_request["status"] == "failed"
    assert pull_request["error"] == "404 Not Found"
