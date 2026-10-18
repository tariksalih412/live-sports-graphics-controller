"""Small helper for API-Football. Every call except 'status' costs 1 request of your daily quota.

  python tools/api_check.py status                   # plan + requests used today
  python tools/api_check.py live                     # all matches being played right now
  python tools/api_check.py date 2026-10-18 [text]   # matches on a day, optional filter (team or league)
  python tools/api_check.py fixture 1234567          # test one fixture end to end

Needs:  $env:API_KEY="..."   (PowerShell)   or   set API_KEY=...   (CMD)
Kick-off times are shown in Qatar time (change TZ below if needed).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.feed import map_api_football  # noqa: E402

BASE = "https://v3.football.api-sports.io"
TZ = "Asia/Qatar"


def get(path, **params):
    url = f"{BASE}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"x-apisports-key": os.environ["API_KEY"]})
    with urllib.request.urlopen(req, timeout=10) as r:
        left = r.headers.get("x-ratelimit-requests-remaining")
        data = json.loads(r.read().decode("utf-8"))
    if left is not None:
        print(f"(requests left today: {left})")
    if data.get("errors"):
        print("API error:", data["errors"])
        sys.exit(1)
    return data


def print_fixtures(items, flt=""):
    flt = flt.lower()
    shown = 0
    for f in items:
        home, away = f["teams"]["home"]["name"], f["teams"]["away"]["name"]
        league = f"{f['league']['country']} - {f['league']['name']}"
        if flt and flt not in f"{home} {away} {league}".lower():
            continue
        st = f["fixture"]["status"]
        when = f["fixture"]["date"][11:16]
        score = f"{f['goals']['home']}-{f['goals']['away']}" if f["goals"]["home"] is not None else "   "
        print(f"{f['fixture']['id']:>9}  {when}  {st['short']:>3} {str(st['elapsed'] or ''):>3}'  "
              f"{score:>5}  {home} vs {away}   [{league}]")
        shown += 1
    print(f"\n{shown} match(es). Use the first number as FIXTURE_ID.")


cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

if cmd == "status":
    d = get("status")["response"]
    print("plan:", d["subscription"]["plan"], "| used today:",
          d["requests"]["current"], "/", d["requests"]["limit_day"])
elif cmd == "live":
    print_fixtures(get("fixtures", live="all", timezone=TZ)["response"],
                   sys.argv[2] if len(sys.argv) > 2 else "")
elif cmd == "date":
    print_fixtures(get("fixtures", date=sys.argv[2], timezone=TZ)["response"],
                   sys.argv[3] if len(sys.argv) > 3 else "")
elif cmd == "fixture":
    raw = get("fixtures", id=sys.argv[2], timezone=TZ)
    s = map_api_football(raw)          # proves our model can read it
    print(f"{s.home.name} {s.home_score} - {s.away_score} {s.away.name} | "
          f"status {s.status} minute {s.minute} | {len(s.events)} events")
    for e in s.events:
        print(f"   {e.minute:>3}'  {e.type:<6} {e.player}")
else:
    print(__doc__)
