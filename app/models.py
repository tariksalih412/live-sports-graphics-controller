from typing import Literal
from pydantic import BaseModel


class Team(BaseModel):
    id: int
    name: str


class Event(BaseModel):
    id: str
    minute: int
    type: Literal["goal", "yellow", "red", "sub", "var", "other"]
    team_id: int
    player: str | None = None
    detail: str | None = None        # "Own Goal", "Penalty", ...


class MatchState(BaseModel):
    match_id: int
    status: str                      # NS, 1H, HT, 2H, ET, P, FT ...
    minute: int | None = None
    home: Team
    away: Team
    home_score: int = 0
    away_score: int = 0
    events: list[Event] = []


class GoalInfo(BaseModel):
    """What the graphics need to know about a goal that really counted."""
    team: Team
    player: str | None = None
    minute: int | None = None
    own_goal: bool = False
    home_score: int
    away_score: int
