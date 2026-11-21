from reflections.analysis.interaction_manifest import interaction_manifest
from reflections.datasources.github import (
    collect_interaction_stream,
    load_interaction_snapshot,
    save_interaction_snapshot,
)


class FakeGithub:
    def __init__(self, responses, remaining=1000):
        self.responses = iter(responses)
        self.rate_limiting = (remaining, 5000)
        self.requester = self
        self.requests = []

    def requestJsonAndCheck(self, method, url, parameters):
        assert method == "GET"
        assert str(parameters["per_page"]) == "100"
        self.requests.append((url, parameters))
        return next(self.responses)


def comment(number, *, review=False):
    parent_field = "pull_request_url" if review else "issue_url"
    parent_kind = "pulls" if review else "issues"
    return {
        "id": 1000 + number,
        parent_field: f"https://api.github.com/repos/org/project/{parent_kind}/{number}",
        "html_url": f"https://github.com/org/project/{parent_kind}/{number}#comment",
        "user": {"login": "person"},
        "author_association": "MEMBER",
        "created_at": f"2020-01-0{number}T00:00:00Z",
        "updated_at": f"2020-01-0{number}T01:00:00Z",
    }


def test_interaction_stream_resumes_cursor_and_round_trips(tmp_path):
    next_url = (
        "https://api.github.com/repositories/1/issues/comments"
        "?per_page=100&after=opaque-cursor"
    )
    first = collect_interaction_stream(
        "org/project",
        "issue_comments",
        github=FakeGithub(
            [
                (
                    {
                        "link": f'<{next_url}>; rel="next"',
                        "x-ratelimit-remaining": "998",
                    },
                    [comment(1)],
                )
            ]
        ),
        request_budget=1,
        quota_floor=500,
    )

    assert not first.complete
    assert first.next_page == 2
    assert first.next_url == next_url
    assert first.records[0].parent_number == 1
    assert first.records[0].kind == "issue_comment"

    path = save_interaction_snapshot(first, tmp_path / "partial.json")
    checkpoint = load_interaction_snapshot(path)
    github = FakeGithub([({"x-ratelimit-remaining": "997"}, [comment(2)])])
    complete = collect_interaction_stream(
        "org/project",
        "issue_comments",
        github=github,
        existing_snapshot=checkpoint,
        request_budget=1,
        quota_floor=500,
    )

    assert complete.complete
    assert complete.requests_used == 2
    assert [item.id for item in complete.records] == [1001, 1002]
    assert github.requests[0][0] == "/repositories/1/issues/comments"
    assert github.requests[0][1]["after"] == "opaque-cursor"


def test_review_comment_stream_maps_pull_request_number():
    snapshot = collect_interaction_stream(
        "org/project",
        "review_comments",
        github=FakeGithub([({}, [comment(3, review=True)])]),
        request_budget=1,
        quota_floor=500,
    )

    assert snapshot.complete
    assert snapshot.interaction_type == "review_comments"
    assert snapshot.records[0].parent_number == 3
    assert snapshot.records[0].kind == "review_comment"
    assert snapshot.records[0].author_association == "MEMBER"


def test_complete_interaction_snapshot_uses_no_more_requests():
    complete = collect_interaction_stream(
        "org/project",
        "issue_comments",
        github=FakeGithub([({}, [])]),
        request_budget=1,
        quota_floor=500,
    )
    github = FakeGithub([])

    cached = collect_interaction_stream(
        "org/project",
        "issue_comments",
        github=github,
        existing_snapshot=complete,
        request_budget=1,
        quota_floor=500,
    )

    assert cached is complete
    assert github.requests == []


def test_interaction_manifest_includes_complete_and_missing(tmp_path):
    complete = collect_interaction_stream(
        "org/project",
        "issue_comments",
        github=FakeGithub([({}, [comment(1)])]),
        request_budget=1,
        quota_floor=500,
    )
    save_interaction_snapshot(
        complete,
        tmp_path / "issue_comments/org--project.json",
    )

    manifest = interaction_manifest(["org/project"], tmp_path)
    statuses = manifest.set_index("interaction_type")["status"].to_dict()

    assert statuses == {
        "issue_comments": "complete",
        "review_comments": "missing",
    }
