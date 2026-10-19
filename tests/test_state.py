from app.models import Event, MatchState, Team
from app.state import diff
from app.formatters import amcp_quote

H, A = Team(id=1, name="H"), Team(id=2, name="A")


def s(hs=0, as_=0, status="1H", minute=10, events=None):
    return MatchState(match_id=1, status=status, minute=minute, home=H, away=A,
                      home_score=hs, away_score=as_, events=events or [])


def kinds(changes):
    return [k for k, _ in changes]


def test_first_snapshot_is_full_sync():
    assert kinds(diff(None, s())) == ["full_sync"]


def test_no_change_no_commands():
    assert diff(s(), s()) == []


def test_goal_triggers_score_and_celebration():
    g = Event(id="g1", minute=11, type="goal", team_id=1, player="P")
    ch = diff(s(minute=11), s(1, 0, minute=11, events=[g]))
    assert kinds(ch) == ["score", "goal"]
    assert ch[1][1].player == "P"


def test_score_before_event_still_celebrates_without_player():
    ch = diff(s(minute=11), s(1, 0, minute=11))
    assert kinds(ch) == ["score", "goal"]
    assert ch[1][1].player is None


def test_late_goal_event_does_not_celebrate_twice():
    g = Event(id="g1", minute=11, type="goal", team_id=1, player="P")
    assert diff(s(1, 0, minute=11), s(1, 0, minute=11, events=[g])) == []


def test_var_cancelled_goal_updates_score_only():
    assert kinds(diff(s(2, 1, minute=70), s(1, 1, minute=70))) == ["score"]


def test_card_detected_once():
    y = Event(id="y1", minute=30, type="yellow", team_id=2, player="X")
    assert kinds(diff(s(minute=30), s(minute=30, events=[y]))) == ["yellow"]
    assert diff(s(minute=30, events=[y]), s(minute=30, events=[y])) == []


def test_status_change_wins_over_clock():
    assert kinds(diff(s(minute=45), s(status="HT", minute=46))) == ["status"]


def test_amcp_quote_escapes_quotes_and_keeps_arabic():
    q = amcp_quote({"name": 'a"b', "ar": "السد"})
    assert q.startswith('"') and q.endswith('"')
    assert '\\"' in q and "السد" in q


def test_own_goal_credits_other_team_and_names_scorer():
    og = Event(id="og", minute=67, type="goal", team_id=2, player="A5", detail="Own Goal")
    ch = diff(s(1, 0, minute=67), s(2, 0, minute=67, events=[og]))
    assert kinds(ch) == ["score", "goal"]
    assert ch[1][1].team.id == 1 and ch[1][1].player == "A5" and ch[1][1].own_goal


def test_goal_player_is_the_new_goal_not_an_old_one():
    g1 = Event(id="g1", minute=12, type="goal", team_id=1, player="First")
    g2 = Event(id="g2", minute=80, type="goal", team_id=1, player="Second")
    ch = diff(s(1, 0, minute=80, events=[g1]), s(2, 0, minute=80, events=[g1, g2]))
    assert ch[1][1].player == "Second"


def test_missed_penalty_is_not_a_goal():
    from app.feed import map_api_football
    raw = {"errors": [], "response": [{
        "fixture": {"id": 1, "status": {"short": "2H", "elapsed": 55}},
        "teams": {"home": {"id": 1, "name": "H"}, "away": {"id": 2, "name": "A"}},
        "goals": {"home": 0, "away": 0},
        "events": [{"time": {"elapsed": 55}, "team": {"id": 1}, "player": {"name": "P"},
                    "type": "Goal", "detail": "Missed Penalty"}]}]}
    assert map_api_football(raw).events[0].type == "other"


# ---- CasparCG command format ----
from app.formatters import CasparFormatter  # noqa: E402


def test_full_sync_adds_scorebug_on_layer_20():
    cmd = CasparFormatter().render("full_sync", s(1, 0))[0]
    assert cmd.startswith("CG 1-20 ADD 1 scorebug 1 ")
    assert '\\"homeScore\\": 1' in cmd


def test_score_update_sends_only_scores():
    cmd = CasparFormatter().render("score", s(2, 1))[0]
    assert cmd.startswith("CG 1-20 UPDATE 1 ") and "home\\\"" not in cmd.split("UPDATE 1 ")[1].replace("homeScore", "")


def test_goal_alert_goes_to_layer_21():
    g = Event(id="g1", minute=11, type="goal", team_id=1, player="P")
    ch = diff(s(minute=11), s(1, 0, minute=11, events=[g]))
    cmd = CasparFormatter().render("goal", ch[1][1])[0]
    assert cmd.startswith("CG 1-21 ADD 1 event_alert 1 ") and '\\"player\\": \\"P\\"' in cmd


def test_goal_alert_sends_home_and_away_scores_separately():
    g = Event(id="g1", minute=11, type="goal", team_id=2, player="P")
    ch = diff(s(minute=11), s(0, 1, minute=11, events=[g]))
    cmd = CasparFormatter().render("goal", ch[1][1])[0]
    assert '\\"homeScore\\": 0' in cmd and '\\"awayScore\\": 1' in cmd
