import random

import pytest

import app
from brainstorm.domain import Board


@pytest.fixture(autouse=True)
def _reset_board():
    app.set_board(Board(random.Random(0)))
    yield


def auth_headers():
    return {"X-Access-Code": app.board.access_code}


def test_missing_access_code_results_in_unauthorized():
    client = app.app.test_client()
    response = client.get("/api/status")
    assert response.status_code == 401


def test_valid_access_code_allows_request():
    client = app.app.test_client()
    response = client.get("/api/status", headers=auth_headers())
    assert response.status_code == 200


def test_join_conflict_on_duplicate_name():
    client = app.app.test_client()
    payload = {"name": "alice", "is_organizer": False}
    first = client.post("/api/join", json=payload, headers=auth_headers())
    assert first.status_code == 200

    second = client.post("/api/join", json=payload, headers=auth_headers())
    assert second.status_code == 409


def test_add_sticky_only_in_generating_phase():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())

    add_generating = client.post(
        "/api/stickies",
        json={"name": "org", "text": "idea", "x": 1, "y": 2},
        headers=auth_headers(),
    )
    assert add_generating.status_code == 201

    client.post(
        "/api/phase",
        json={"name": "org", "phase": "VOTING"},
        headers=auth_headers(),
    )

    add_voting = client.post(
        "/api/stickies",
        json={"name": "org", "text": "idea2", "x": 3, "y": 4},
        headers=auth_headers(),
    )
    assert add_voting.status_code == 403


def test_phase_change_requires_organizer():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "alice", "is_organizer": False}, headers=auth_headers())

    forbidden = client.post(
        "/api/phase",
        json={"name": "alice", "phase": "VOTING"},
        headers=auth_headers(),
    )
    assert forbidden.status_code == 403

    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())
    allowed = client.post(
        "/api/phase",
        json={"name": "org", "phase": "VOTING"},
        headers=auth_headers(),
    )
    assert allowed.status_code == 200


def test_vote_limit_enforced():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())
    client.post("/api/join", json={"name": "bob", "is_organizer": False}, headers=auth_headers())

    note_resp = client.post(
        "/api/stickies",
        json={"name": "org", "text": "idea", "x": 0, "y": 0},
        headers=auth_headers(),
    )
    note_id = note_resp.get_json()["id"]

    client.post(
        "/api/phase",
        json={"name": "org", "phase": "VOTING"},
        headers=auth_headers(),
    )

    first_vote = client.post(
        "/api/votes",
        json={"name": "bob", "sticky_id": note_id, "points": 5},
        headers=auth_headers(),
    )
    assert first_vote.status_code == 200

    second_vote = client.post(
        "/api/votes",
        json={"name": "bob", "sticky_id": note_id, "points": 6},
        headers=auth_headers(),
    )
    assert second_vote.status_code == 400


def test_sticky_text_length_limit_rejected():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())
    long_text = "x" * 201

    response = client.post(
        "/api/stickies",
        json={"name": "org", "text": long_text, "x": 1, "y": 2},
        headers=auth_headers(),
    )
    assert response.status_code == 400


def test_sticky_limit_per_participant_enforced():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())
    for i in range(50):
        response = client.post(
            "/api/stickies",
            json={"name": "org", "text": f"note {i}", "x": 1, "y": 2},
            headers=auth_headers(),
        )
        assert response.status_code == 201

    overflow = client.post(
        "/api/stickies",
        json={"name": "org", "text": "overflow", "x": 1, "y": 2},
        headers=auth_headers(),
    )
    assert overflow.status_code == 400


def test_finished_phase_forbids_modifications():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())
    client.post("/api/join", json={"name": "bob", "is_organizer": False}, headers=auth_headers())

    note_resp = client.post(
        "/api/stickies",
        json={"name": "org", "text": "idea", "x": 0, "y": 0},
        headers=auth_headers(),
    )
    note_id = note_resp.get_json()["id"]

    client.post(
        "/api/phase",
        json={"name": "org", "phase": "VOTING"},
        headers=auth_headers(),
    )
    client.post(
        "/api/phase",
        json={"name": "org", "phase": "FINISHED"},
        headers=auth_headers(),
    )

    add_resp = client.post(
        "/api/stickies",
        json={"name": "org", "text": "late", "x": 1, "y": 1},
        headers=auth_headers(),
    )
    assert add_resp.status_code == 403

    move_resp = client.post(
        f"/api/stickies/{note_id}/move",
        json={"name": "org", "x": 2, "y": 2},
        headers=auth_headers(),
    )
    assert move_resp.status_code == 403

    delete_resp = client.delete(
        f"/api/stickies/{note_id}",
        json={"name": "org"},
        headers=auth_headers(),
    )
    assert delete_resp.status_code == 403

    vote_resp = client.post(
        "/api/votes",
        json={"name": "bob", "sticky_id": note_id, "points": 1},
        headers=auth_headers(),
    )
    assert vote_resp.status_code == 403


def test_reset_clears_state_and_changes_access_code():
    client = app.app.test_client()
    client.post("/api/join", json={"name": "org", "is_organizer": True}, headers=auth_headers())
    before_reset_code = app.board.access_code

    response = client.post("/api/reset", json={"name": "org"}, headers=auth_headers())
    assert response.status_code == 200
    after_reset_code = response.get_json()["access_code"]
    assert before_reset_code != after_reset_code

    status_resp = client.get("/api/status", headers={"X-Access-Code": after_reset_code})
    assert status_resp.status_code == 200
    assert status_resp.get_json()["participants_count"] == 0
