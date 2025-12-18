from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

from brainstorm.domain import (
    Board,
    ForbiddenInPhase,
    InvalidPhaseTransition,
    NameAlreadyExists,
    NotAuthor,
    NotFound,
    NotOrganizer,
    Phase,
    VoteLimitExceeded,
)

app = Flask(__name__)
board: Board = Board()


def set_board(new_board: Board) -> None:
    global board
    board = new_board


def _require_access_code() -> Any:
    code = request.headers.get("X-Access-Code") or request.args.get("access_code")
    if code != board.access_code:
        return jsonify({"error": "invalid access code"}), 401
    return None


@app.before_request
def check_access_code() -> Any:
    if request.path.startswith("/api/"):
        return _require_access_code()
    return None


def _bad_request(message: str):
    return jsonify({"error": message}), 400


@app.errorhandler(NameAlreadyExists)
def handle_name_conflict(_: NameAlreadyExists):
    return jsonify({"error": "name already taken"}), 409


@app.errorhandler(NotOrganizer)
def handle_not_organizer(_: NotOrganizer):
    return jsonify({"error": "not organizer"}), 403


@app.errorhandler(InvalidPhaseTransition)
def handle_invalid_phase(_: InvalidPhaseTransition):
    return _bad_request("invalid phase transition")


@app.errorhandler(ForbiddenInPhase)
def handle_forbidden_phase(_: ForbiddenInPhase):
    return jsonify({"error": "forbidden in current phase"}), 403


@app.errorhandler(VoteLimitExceeded)
def handle_vote_limit(_: VoteLimitExceeded):
    return _bad_request("vote limit exceeded")


@app.errorhandler(NotAuthor)
def handle_not_author(_: NotAuthor):
    return jsonify({"error": "not author"}), 403


@app.errorhandler(NotFound)
def handle_not_found(_: NotFound):
    return jsonify({"error": "not found"}), 404


@app.route("/")
def index():
    return render_template("index.html", access_code=board.access_code)


@app.route("/board")
def board_view():
    return render_template("board.html", access_code=board.access_code)


@app.route("/api/status")
def status():
    return jsonify(
        {
            "phase": board.phase.value,
            "participants_count": len(board.participants),
            "notes_count": len(board.notes),
            "votes_count": len(board.votes),
        }
    )


def _get_json_payload() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Invalid JSON payload")
    return data


@app.route("/api/join", methods=["POST"])
def join():
    try:
        payload = _get_json_payload()
        name = payload.get("name")
        is_organizer = payload.get("is_organizer")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or not isinstance(name, str):
        return _bad_request("name is required")
    if not isinstance(is_organizer, bool):
        return _bad_request("is_organizer must be boolean")

    participant = board.join(name=name, is_organizer=is_organizer)
    return jsonify(asdict(participant))


@app.route("/api/board")
def board_state():
    votes_by_note: Dict[str, Dict[str, int]] = {}
    for participant_name, allocations in board.votes.items():
        for note_id, points in allocations.items():
            votes_by_note.setdefault(note_id, {})[participant_name] = points

    return jsonify(
        {
            "phase": board.phase.value,
            "participants": [asdict(p) for p in board.participants.values()],
            "stickies": [
                {
                    **asdict(note),
                    "created_at": note.created_at.isoformat() + "Z",
                }
                for note in board.notes.values()
            ],
            "votes": votes_by_note,
            "scores": {note_id: board.note_score(note_id) for note_id in board.notes},
        }
    )


@app.route("/api/stickies", methods=["POST"])
def add_sticky():
    try:
        payload = _get_json_payload()
        name = payload.get("name")
        text = payload.get("text")
        x = payload.get("x")
        y = payload.get("y")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or not isinstance(name, str):
        return _bad_request("name is required")
    if not isinstance(text, str) or text == "":
        return _bad_request("text is required")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return _bad_request("coordinates must be numeric")

    note = board.add_note(author_name=name, text=text, x=float(x), y=float(y))
    return jsonify(
        {
            **asdict(note),
            "created_at": note.created_at.isoformat() + "Z",
        }
    ), 201


@app.route("/api/stickies/<note_id>/move", methods=["POST"])
def move_sticky(note_id: str):
    try:
        payload = _get_json_payload()
        name = payload.get("name")
        x = payload.get("x")
        y = payload.get("y")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or name not in board.participants:
        return _bad_request("unknown participant")
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        return _bad_request("coordinates must be numeric")

    board.move_note(note_id, float(x), float(y))
    return jsonify({"status": "moved"})


@app.route("/api/stickies/<note_id>", methods=["DELETE"])
def delete_sticky(note_id: str):
    try:
        payload = _get_json_payload()
        name = payload.get("name")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or not isinstance(name, str):
        return _bad_request("name is required")

    board.delete_note(note_id, requester=name)
    return jsonify({"status": "deleted"})


@app.route("/api/phase", methods=["POST"])
def change_phase():
    try:
        payload = _get_json_payload()
        name = payload.get("name")
        phase_value = payload.get("phase")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or not isinstance(name, str):
        return _bad_request("name is required")
    try:
        new_phase = Phase(phase_value)
    except Exception:
        return _bad_request("invalid phase")

    board.change_phase(requester=name, new_phase=new_phase)
    return jsonify({"phase": board.phase.value})


@app.route("/api/votes", methods=["POST"])
def set_vote():
    try:
        payload = _get_json_payload()
        name = payload.get("name")
        sticky_id = payload.get("sticky_id")
        points = payload.get("points")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or not isinstance(name, str):
        return _bad_request("name is required")
    if not sticky_id or not isinstance(sticky_id, str):
        return _bad_request("sticky_id is required")
    if not isinstance(points, int):
        return _bad_request("points must be integer")

    board.set_vote(participant_name=name, note_id=sticky_id, points=points)
    return jsonify({"status": "ok"})


@app.route("/api/reset", methods=["POST"])
def reset_board():
    try:
        payload = _get_json_payload()
        name = payload.get("name")
    except ValueError as exc:
        return _bad_request(str(exc))

    if not name or not isinstance(name, str):
        return _bad_request("name is required")

    board.reset(requester=name)
    return jsonify({"status": "reset", "access_code": board.access_code})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
