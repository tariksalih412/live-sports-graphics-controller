"""Rebuild a finished match minute by minute from its final data, so it can be
replayed on CasparCG as if it were live. Costs ONE request (or none with a saved file).

  python tools/rebuild_match.py 1234567            # fetch from API-Football (1 request)
  python tools/rebuild_match.py saved_match.json   # use a file you already have

Output: tools/recordings/rebuilt/<fixture_id>/0000.json, 0001.json ...
Then:   $env:REPLAY_DIR="tools/recordings/rebuilt/<fixture_id>"; python -m app.main
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(arg: str) -> dict:
    p = Path(arg)
    if p.suffix == ".json" and p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    url = f"https://v3.football.api-sports.io/fixtures?id={arg}"
    req = urllib.request.Request(url, headers={"x-apisports-key": os.environ["API_KEY"]})
    with urllib.request.urlopen(req, timeout=10) as r:
        print("requests left today:", r.headers.get("x-ratelimit-requests-remaining"))
        raw = json.loads(r.read().decode("utf-8"))
    if raw.get("errors"):
        sys.exit(f"API error: {raw['errors']}")
    if not raw.get("response"):
        sys.exit("no fixture returned, check the id")
    saved = ROOT / "tools" / "recordings" / "full" / f"{arg}.json"
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    print("saved original response to", saved)
    return raw


def when(e) -> tuple[int, int]:
    return e["time"]["elapsed"], e["time"].get("extra") or 0


def is_shootout(e) -> bool:
    return "shootout" in (e.get("comments") or "").lower()


def is_goal(e) -> bool:
    return e["type"] == "Goal" and "Missed" not in e.get("detail", "") and not is_shootout(e)


def score_at(events, upto, home_id, flip_own_goals):
    h = a = 0
    for e in events:
        if when(e) > upto or not is_goal(e):
            continue
        team = e["team"]["id"]
        if flip_own_goals and e.get("detail") == "Own Goal":
            team = None if team == home_id else home_id   # credit the other side
        if team == home_id:
            h += 1
        else:
            a += 1
    return h, a


def main():
    raw = load(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
    m = raw["response"][0]
    fid = m["fixture"]["id"]
    home_id = m["teams"]["home"]["id"]
    final = (m["goals"]["home"] or 0, m["goals"]["away"] or 0)
    # Penalty shoot-out kicks are not part of the match score; leave them out of the replay
    events = sorted((e for e in m.get("events", []) if not is_shootout(e)), key=when)

    # Own goals: providers differ on which team they list. Pick the reading that matches the final score.
    flip = False
    end = (999, 99)
    complete = True
    if score_at(events, end, home_id, False) != final:
        if score_at(events, end, home_id, True) == final:
            flip = True
        else:
            complete = False

    def stoppage(period_end):
        extras = [when(e)[1] for e in events if when(e)[0] == period_end]
        return max(extras, default=0)

    # Timeline of (status, displayed minute, cut-off for events)
    ticks = [("NS", None, (0, 0))]
    ticks += [("1H", t, (t, 0)) for t in range(1, 46)]
    ticks += [("1H", 45, (45, x)) for x in range(1, stoppage(45) + 1)]
    ticks += [("HT", 45, (45, 99))] * 3
    ticks += [("2H", t, (t, 0)) for t in range(46, 91)]
    ticks += [("2H", 90, (90, x)) for x in range(1, stoppage(90) + 1)]
    if any(when(e)[0] > 90 for e in events) or m["fixture"]["status"]["short"] in ("AET", "PEN"):
        ticks += [("BT", 90, (90, 99))] * 2
        ticks += [("ET", t, (t, 0)) for t in range(91, 121)]
        ticks += [("ET", 120, (120, x)) for x in range(1, stoppage(120) + 1)]
    ticks += [(m["fixture"]["status"]["short"] or "FT", None, end)] * 2

    out = ROOT / "tools" / "recordings" / "rebuilt" / str(fid)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.json"):
        old.unlink()

    for i, (status, minute, cut) in enumerate(ticks):
        shown = [e for e in events if when(e) <= cut]
        if status == "NS":
            h, a = 0, 0
        elif cut == end:
            h, a = final                  # full time always shows the official result
        else:
            h, a = score_at(events, cut, home_id, flip)
        snap = {"errors": [], "response": [{
            "fixture": {"id": fid, "status": {"short": status,
                                               "elapsed": minute if minute is not None else (90 if status != "NS" else None)}},
            "teams": m["teams"],
            "goals": {"home": h, "away": a},
            "events": shown,
        }]}
        (out / f"{i:04d}.json").write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")

    th, ta = m["teams"]["home"]["name"], m["teams"]["away"]["name"]
    print(f"{th} {final[0]} - {final[1]} {ta}: {len(events)} events -> {len(ticks)} snapshots in {out}")
    for e in events:
        el, ex = when(e)
        mark = f"{el}+{ex}" if ex else f"{el}"
        print(f"   {mark:>6}'  {e['type']:<6} {e.get('detail',''):<16} {(e.get('player') or {}).get('name')}")
    if not complete:
        got = score_at(events, end, home_id, flip)
        print("\n" + "!" * 70)
        print(f"!! WARNING: the goal events add up to {got[0]}-{got[1]}, the official result is {final[0]}-{final[1]}.")
        print("!! The provider has no (or incomplete) event data for this match, usual for youth")
        print("!! and lower leagues. Goals will not appear minute by minute; only full time is right.")
        print("!! Choose a match from a top league for testing and for the demo.")
        print("!" * 70)
    print(f'\nnext:  $env:REPLAY_DIR="tools/recordings/rebuilt/{fid}"; $env:POLL_INTERVAL="0.5"; python -m app.main')


main()
