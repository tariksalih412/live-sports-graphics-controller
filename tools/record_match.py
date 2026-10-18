"""Record a real match into replay files.
  python tools/record_match.py 90          # one snapshot every 90 s (default)

Needs API_KEY and FIXTURE_ID. Start it at kick-off, not before: on the free plan
(100 requests/day) a full match at 90 s is about 80 requests.
Stops at full time, or when fewer than 5 requests are left today.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

INTERVAL = int(sys.argv[1]) if len(sys.argv) > 1 else 90
FIXTURE_ID = os.environ["FIXTURE_ID"]
OUT = Path("tools/recordings/live") / FIXTURE_ID
URL = f"https://v3.football.api-sports.io/fixtures?id={FIXTURE_ID}"
FINISHED = {"FT", "AET", "PEN", "PST", "CANC", "ABD", "AWD", "WO"}

OUT.mkdir(parents=True, exist_ok=True)
n = len(list(OUT.glob("*.json")))           # continue numbering if restarted
print(f"recording fixture {FIXTURE_ID} every {INTERVAL}s into {OUT}")

while True:
    try:
        req = urllib.request.Request(URL, headers={"x-apisports-key": os.environ["API_KEY"]})
        with urllib.request.urlopen(req, timeout=10) as r:
            left = int(r.headers.get("x-ratelimit-requests-remaining", "999"))
            raw = json.loads(r.read().decode("utf-8"))
    except Exception as e:                   # network glitch: wait and try again, don't crash
        print("request failed:", e)
        time.sleep(INTERVAL)
        continue

    if raw.get("errors"):
        print("API error, stopping:", raw["errors"])
        break
    if not raw.get("response"):
        print("no fixture returned, check FIXTURE_ID")
        break

    m = raw["response"][0]
    (OUT / f"{n:04d}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
    st = m["fixture"]["status"]
    print(f"saved {n:04d}  {st['short']} {st['elapsed']}'  "
          f"{m['goals']['home']}-{m['goals']['away']}  events={len(m.get('events', []))}  left={left}")
    n += 1

    if st["short"] in FINISHED:
        print("match finished")
        break
    if left < 5:
        print("daily quota almost used, stopping")
        break
    time.sleep(INTERVAL)
