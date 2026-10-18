"""Delta detection: compare the previous snapshot with the new one and return
only the changes the graphics care about."""
from .models import GoalInfo, MatchState


def _benefits(e, state: MatchState) -> int:
    """Team that gets the goal: for an own goal, the other side of the listed team."""
    if e.detail == "Own Goal":
        return state.away.id if e.team_id == state.home.id else state.home.id
    return e.team_id


def _new_goal_for(old: MatchState, new: MatchState, team_id: int):
    seen = {e.id for e in old.events}
    goals = [e for e in new.events
             if e.type == "goal" and e.id not in seen and _benefits(e, new) == team_id]
    return goals[-1] if goals else None


def diff(old: MatchState | None, new: MatchState) -> list[tuple[str, object]]:
    if old is None:
        return [("full_sync", new)]

    changes: list[tuple[str, object]] = []

    # Score: always update the numbers; celebrate only when a score INCREASES.
    # A decrease means a VAR-cancelled goal -> numbers change, no animation.
    if (old.home_score, old.away_score) != (new.home_score, new.away_score):
        changes.append(("score", new))
        for team, before, after in ((new.home, old.home_score, new.home_score),
                                    (new.away, old.away_score, new.away_score)):
            if after > before:
                g = _new_goal_for(old, new, team.id)   # event may arrive later than the score
                changes.append(("goal", GoalInfo(
                    team=team,
                    player=g.player if g else None,
                    minute=g.minute if g else new.minute,
                    own_goal=bool(g and g.detail == "Own Goal"),
                    home_score=new.home_score, away_score=new.away_score)))

    # Cards: new event ids only
    seen = {e.id for e in old.events}
    for e in new.events:
        if e.id not in seen and e.type in ("yellow", "red"):
            changes.append((e.type, e))

    if old.status != new.status:
        changes.append(("status", new))
    elif old.minute != new.minute:
        changes.append(("clock", new))

    return changes
