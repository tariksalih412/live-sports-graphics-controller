"""Generates a fake match in API-Football format so you can work without an API key.
Scenario: goal 23', yellow 30', half time, away goal 61', home goal 70' cancelled by VAR,
red card 78', home goal 85', full time."""
import json
from pathlib import Path

OUT = Path(__file__).parent / "recordings"
HOME = {"id": 1, "name": "السد"}
AWAY = {"id": 2, "name": "الدحيل"}


def ev(minute, team, typ, detail, player):
    return {"time": {"elapsed": minute}, "team": team, "player": {"name": player},
            "type": typ, "detail": detail}


def snap(status, minute, hs, as_, events):
    return {"response": [{
        "fixture": {"id": 999, "status": {"short": status, "elapsed": minute}},
        "teams": {"home": HOME, "away": AWAY},
        "goals": {"home": hs, "away": as_},
        "events": events}]}


g1 = ev(23, HOME, "Goal", "Normal Goal", "أكرم عفيف")
y1 = ev(30, AWAY, "Card", "Yellow Card", "المعز علي")
g2 = ev(61, AWAY, "Goal", "Normal Goal", "المعز علي")
g3 = ev(70, HOME, "Goal", "Normal Goal", "حسن الهيدوس")
var = ev(71, HOME, "Var", "Goal cancelled", "حسن الهيدوس")
r1 = ev(78, AWAY, "Card", "Red Card", "لوكاس أوكامبوس")
g4 = ev(85, HOME, "Goal", "Normal Goal", "أكرم عفيف")

frames = [
    snap("NS", None, 0, 0, []),
    snap("1H", 1, 0, 0, []),
    snap("1H", 15, 0, 0, []),
    snap("1H", 23, 1, 0, []),          # score arrives before the event
    snap("1H", 24, 1, 0, [g1]),
    snap("1H", 30, 1, 0, [g1, y1]),
    snap("1H", 45, 1, 0, [g1, y1]),
    snap("HT", 45, 1, 0, [g1, y1]),
    snap("2H", 46, 1, 0, [g1, y1]),
    snap("2H", 61, 1, 1, [g1, y1, g2]),
    snap("2H", 70, 2, 1, [g1, y1, g2, g3]),
    snap("2H", 71, 1, 1, [g1, y1, g2, var]),   # VAR: score goes back down
    snap("2H", 78, 1, 1, [g1, y1, g2, var, r1]),
    snap("2H", 85, 2, 1, [g1, y1, g2, var, r1, g4]),
    snap("2H", 90, 2, 1, [g1, y1, g2, var, r1, g4]),
    snap("FT", 90, 2, 1, [g1, y1, g2, var, r1, g4]),
]

OUT.mkdir(exist_ok=True)
for i, f in enumerate(frames):
    (OUT / f"{i:04d}.json").write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {len(frames)} snapshots to {OUT}")
