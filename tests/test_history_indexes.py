from datetime import UTC, datetime

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
