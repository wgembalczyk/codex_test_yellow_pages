import random
import string
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class NameAlreadyExists(Exception):
    pass


class NotOrganizer(Exception):
    pass


class InvalidPhaseTransition(Exception):
    pass


class ForbiddenInPhase(Exception):
    pass


class VoteLimitExceeded(Exception):
    pass


class NotAuthor(Exception):
    pass


class NotFound(Exception):
    pass


class Phase(str, Enum):
    GENERATING = "GENERATING"
    VOTING = "VOTING"
    FINISHED = "FINISHED"


COLORS = ["#fff59d", "#ffe082", "#ffcc80", "#c5e1a5", "#fff176", "#ffd180"]


@dataclass
class Participant:
    name: str
    is_organizer: bool
    color: str


@dataclass
class Note:
    id: str
    text: str
    author_name: str
    color: str
    x: float
    y: float
    created_at: datetime


class Board:
    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.phase = Phase.GENERATING
        self.participants: Dict[str, Participant] = {}
        self.notes: Dict[str, Note] = {}
        self.votes: Dict[str, Dict[str, int]] = {}
        self.access_code = self._generate_access_code()

    def _generate_access_code(self, length: int = 6) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(self.rng.choice(alphabet) for _ in range(length))

    def _require_organizer(self, name: str) -> None:
        participant = self.participants.get(name)
        if not participant or not participant.is_organizer:
            raise NotOrganizer()

    def join(self, name: str, is_organizer: bool) -> Participant:
        if name in self.participants:
            raise NameAlreadyExists()
        color = self.rng.choice(COLORS)
        participant = Participant(name=name, is_organizer=is_organizer, color=color)
        self.participants[name] = participant
        return participant

    def add_note(self, author_name: str, text: str, x: float, y: float) -> Note:
        if self.phase is not Phase.GENERATING:
            raise ForbiddenInPhase()
        author = self.participants.get(author_name)
        if not author:
            raise NotFound()
        note_id = str(uuid.UUID(int=self.rng.getrandbits(128)))
        note = Note(
            id=note_id,
            text=text,
            author_name=author.name,
            color=author.color,
            x=x,
            y=y,
            created_at=datetime.utcnow(),
        )
        self.notes[note_id] = note
        return note

    def move_note(self, note_id: str, x: float, y: float) -> None:
        if self.phase is Phase.FINISHED:
            raise ForbiddenInPhase()
        note = self.notes.get(note_id)
        if not note:
            raise NotFound()
        note.x = x
        note.y = y

    def delete_note(self, note_id: str, requester: str) -> None:
        if self.phase is Phase.FINISHED:
            raise ForbiddenInPhase()
        note = self.notes.get(note_id)
        if not note:
            raise NotFound()
        if note.author_name != requester:
            raise NotAuthor()
        del self.notes[note_id]
        for allocations in self.votes.values():
            allocations.pop(note_id, None)

    def change_phase(self, requester: str, new_phase: Phase) -> None:
        self._require_organizer(requester)
        if new_phase == self.phase:
            return
        allowed = {
            Phase.GENERATING: Phase.VOTING,
            Phase.VOTING: Phase.FINISHED,
        }
        if allowed.get(self.phase) != new_phase:
            raise InvalidPhaseTransition()
        self.phase = new_phase

    def set_vote(self, participant_name: str, note_id: str, points: int) -> None:
        if self.phase is not Phase.VOTING:
            raise ForbiddenInPhase()
        if points < 0 or points > 5:
            raise VoteLimitExceeded()
        participant = self.participants.get(participant_name)
        if not participant:
            raise NotFound()
        if note_id not in self.notes:
            raise NotFound()
        allocations = self.votes.setdefault(participant_name, {})
        current_total = sum(allocations.values()) - allocations.get(note_id, 0)
        if current_total + points > 5:
            raise VoteLimitExceeded()
        allocations[note_id] = points

    def note_score(self, note_id: str) -> int:
        return sum(votes.get(note_id, 0) for votes in self.votes.values())

    def reset(self, requester: str) -> None:
        self._require_organizer(requester)
        self.phase = Phase.GENERATING
        self.participants.clear()
        self.notes.clear()
        self.votes.clear()
        self.access_code = self._generate_access_code()
