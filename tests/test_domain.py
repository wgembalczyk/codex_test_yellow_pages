import random

import pytest

from brainstorm.domain import (
    Board,
    ForbiddenInPhase,
    InvalidPhaseTransition,
    NameAlreadyExists,
    NoteTextTooLong,
    NotAuthor,
    NotFound,
    NotOrganizer,
    Phase,
    StickyLimitExceeded,
    VoteLimitExceeded,
)


def test_join_requires_unique_name():
    board = Board(rng=random.Random(1))
    board.join("alice", True)
    with pytest.raises(NameAlreadyExists):
        board.join("alice", False)


def test_join_assigns_deterministic_color_and_access_code():
    board = Board(rng=random.Random(1))
    participant = board.join("alice", True)
    assert participant.color == "#c5e1a5"
    assert board.access_code == "IEQH52"


def test_only_organizer_can_change_phase_and_reset():
    board = Board(rng=random.Random(1))
    board.join("org", True)
    board.join("bob", False)
    with pytest.raises(NotOrganizer):
        board.change_phase("bob", Phase.VOTING)
    board.change_phase("org", Phase.VOTING)
    assert board.phase == Phase.VOTING
    with pytest.raises(NotOrganizer):
        board.reset("bob")


def test_invalid_phase_transition():
    board = Board(rng=random.Random(0))
    board.join("org", True)
    with pytest.raises(InvalidPhaseTransition):
        board.change_phase("org", Phase.FINISHED)
    board.change_phase("org", Phase.VOTING)
    with pytest.raises(InvalidPhaseTransition):
        board.change_phase("org", Phase.GENERATING)


def test_add_move_delete_notes_respects_phases_and_authorship():
    board = Board(rng=random.Random(2))
    board.join("org", True)
    board.join("alice", False)
    note = board.add_note("alice", "idea", 1, 2)
    assert note.color == board.participants["alice"].color

    board.change_phase("org", Phase.VOTING)
    board.move_note(note.id, 3, 4)
    assert board.notes[note.id].x == 3

    board.change_phase("org", Phase.FINISHED)
    with pytest.raises(ForbiddenInPhase):
        board.move_note(note.id, 5, 6)
    with pytest.raises(ForbiddenInPhase):
        board.add_note("alice", "another", 0, 0)
    with pytest.raises(ForbiddenInPhase):
        board.delete_note(note.id, "alice")


def test_delete_requires_author():
    board = Board(rng=random.Random(3))
    board.join("org", True)
    board.join("alice", False)
    board.join("bob", False)
    note = board.add_note("alice", "idea", 1, 2)
    with pytest.raises(NotAuthor):
        board.delete_note(note.id, "bob")
    board.delete_note(note.id, "alice")
    assert note.id not in board.notes


def test_voting_limits_and_allocation_changes():
    board = Board(rng=random.Random(4))
    board.join("org", True)
    board.join("alice", False)
    note1 = board.add_note("alice", "a", 0, 0)
    note2 = board.add_note("alice", "b", 0, 0)
    board.change_phase("org", Phase.VOTING)
    board.set_vote("alice", note1.id, 3)
    board.set_vote("alice", note2.id, 2)
    assert board.note_score(note1.id) == 3
    assert board.note_score(note2.id) == 2
    with pytest.raises(VoteLimitExceeded):
        board.set_vote("alice", note2.id, 4)
    board.set_vote("alice", note1.id, 1)
    assert board.note_score(note1.id) == 1
    assert board.note_score(note2.id) == 2


def test_voting_only_allowed_in_voting_phase():
    board = Board(rng=random.Random(5))
    board.join("org", True)
    board.join("alice", False)
    note = board.add_note("alice", "a", 0, 0)
    with pytest.raises(ForbiddenInPhase):
        board.set_vote("alice", note.id, 1)
    board.change_phase("org", Phase.VOTING)
    board.set_vote("alice", note.id, 1)
    board.change_phase("org", Phase.FINISHED)
    with pytest.raises(ForbiddenInPhase):
        board.set_vote("alice", note.id, 0)


def test_note_text_length_limit():
    board = Board(rng=random.Random(8))
    board.join("org", True)
    long_text = "x" * 201
    with pytest.raises(NoteTextTooLong):
        board.add_note("org", long_text, 0, 0)


def test_sticky_limit_per_participant():
    board = Board(rng=random.Random(9))
    board.join("org", True)
    for i in range(50):
        board.add_note("org", f"note {i}", 0, 0)
    with pytest.raises(StickyLimitExceeded):
        board.add_note("org", "overflow", 0, 0)


def test_reset_clears_state_and_regenerates_access_code():
    board = Board(rng=random.Random(6))
    board.join("org", True)
    board.join("alice", False)
    note = board.add_note("alice", "a", 0, 0)
    board.change_phase("org", Phase.VOTING)
    board.set_vote("alice", note.id, 5)
    old_code = board.access_code
    board.reset("org")
    assert board.participants == {}
    assert board.notes == {}
    assert board.votes == {}
    assert board.phase == Phase.GENERATING
    assert board.access_code != old_code


def test_missing_entities_raise_not_found():
    board = Board(rng=random.Random(7))
    board.join("org", True)
    with pytest.raises(NotFound):
        board.add_note("missing", "idea", 0, 0)
    with pytest.raises(NotFound):
        board.move_note("unknown", 0, 0)
    board.change_phase("org", Phase.VOTING)
    with pytest.raises(NotFound):
        board.set_vote("org", "missing", 1)
