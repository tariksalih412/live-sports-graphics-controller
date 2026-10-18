import json
from pathlib import Path

import aiohttp

from .models import Event, MatchState, Team


def map_api_football(raw: dict) -> MatchState:
    """Convert an API-Football /fixtures response into our internal model.
    Check field names against the provider docs if you switch providers."""
    errors = raw.get("errors")
    if errors:                        # e.g. bad key, quota reached, season not in free plan
        raise ValueError(f"API error: {errors}")
    if not raw.get("response"):
        raise ValueError("API returned no fixture (check FIXTURE_ID)")
    m = raw["response"][0]
    events = []
    for e in m.get("events", []):
        if "shootout" in (e.get("comments") or "").lower():
            continue                      # shoot-out kicks don't change the match score
        t = e.get("type", "")
        if t == "Goal":
            kind = "other" if "Missed" in e.get("detail", "") else "goal"
        elif t == "Card":
            kind = "red" if "Red" in e.get("detail", "") else "yellow"
        elif t == "subst":
            kind = "sub"
        elif t == "Var":
            kind = "var"
        else:
            kind = "other"
        player = (e.get("player") or {}).get("name")
        minute = e["time"]["elapsed"]
        eid = f'{minute}-{t}-{e["team"]["id"]}-{player}'
        events.append(Event(id=eid, minute=minute, type=kind,
                            team_id=e["team"]["id"], player=player, detail=e.get("detail")))
    return MatchState(
        match_id=m["fixture"]["id"],
        status=m["fixture"]["status"]["short"],
        minute=m["fixture"]["status"]["elapsed"],
        home=Team(id=m["teams"]["home"]["id"], name=m["teams"]["home"]["name"]),
        away=Team(id=m["teams"]["away"]["id"], name=m["teams"]["away"]["name"]),
        home_score=m["goals"]["home"] or 0,
        away_score=m["goals"]["away"] or 0,
        events=events,
    )


class LiveFeed:
    URL = "https://v3.football.api-sports.io/fixtures"

    def __init__(self, session: aiohttp.ClientSession, api_key: str, fixture_id: int):
        self.s, self.key, self.fid = session, api_key, fixture_id

    async def fetch_raw(self) -> dict:
        async with self.s.get(self.URL, params={"id": self.fid},
                              headers={"x-apisports-key": self.key},
                              timeout=aiohttp.ClientTimeout(total=5)) as r:
            r.raise_for_status()
            return await r.json()

    async def fetch(self) -> MatchState:
        return map_api_football(await self.fetch_raw())


class ReplayFeed:
    """Plays back recorded snapshots in order, then stays on the last one."""

    def __init__(self, folder: str):
        self.files = sorted(Path(folder).glob("*.json"))
        if not self.files:
            raise FileNotFoundError(f"no .json snapshots in {folder}")
        self.i = 0

    async def fetch(self) -> MatchState:
        f = self.files[min(self.i, len(self.files) - 1)]
        self.i += 1
        return map_api_football(json.loads(f.read_text(encoding="utf-8")))
