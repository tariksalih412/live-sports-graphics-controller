"""Turn changes into CasparCG AMCP commands."""
import json

from . import config
from .models import Event, GoalInfo, MatchState


def tpl(name: str) -> str:
    """Template reference for CG ADD: a name in CasparCG's template folder,
    or a full URL when TEMPLATE_BASE is set."""
    if config.TEMPLATE_BASE:
        base = config.TEMPLATE_BASE.rstrip("/")
        return '"' + base + "/" + name + '.html"'
    return name


def amcp_quote(data: dict) -> str:
    """JSON inside an AMCP string: escape backslashes and double quotes."""
    s = json.dumps(data, ensure_ascii=False)
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


class CasparFormatter:
    terminator = b"\r\n"

    def __init__(self):
        ch = config.CASPAR_CHANNEL
        self.bug = f"{ch}-{config.SCOREBUG_LAYER}"
        self.alert = f"{ch}-{config.ALERT_LAYER}"

    @staticmethod
    def _scorebug_data(s: MatchState) -> dict:
        return {"home": s.home.name, "away": s.away.name,
                "homeScore": s.home_score, "awayScore": s.away_score,
                "minute": s.minute, "status": s.status}

    def render(self, kind: str, data) -> list[str]:
        scorebug, alert = tpl("scorebug"), tpl("event_alert")
        if kind == "full_sync":
            # CG <channel-layer> ADD <cg_layer> <template> <play_on_load> <data>
            return [f"CG {self.bug} ADD 1 {scorebug} 1 {amcp_quote(self._scorebug_data(data))}"]
        if kind == "score":
            return [f"CG {self.bug} UPDATE 1 "
                    + amcp_quote({"homeScore": data.home_score, "awayScore": data.away_score})]
        if kind in ("clock", "status"):
            return [f"CG {self.bug} UPDATE 1 "
                    + amcp_quote({"minute": data.minute, "status": data.status})]
        if kind == "goal":
            g: GoalInfo = data
            player = (g.player or "") + (" (هدف عكسي)" if g.own_goal and g.player else "")
            payload = {"kind": "goal", "team": g.team.name, "player": player,
                       "minute": g.minute, "homeScore": g.home_score, "awayScore": g.away_score}
            return [f"CG {self.alert} ADD 1 {alert} 1 {amcp_quote(payload)}"]
        if kind in ("yellow", "red"):
            e: Event = data
            payload = {"kind": kind, "player": e.player or "", "minute": e.minute,
                       "homeScore": None, "awayScore": None}
            return [f"CG {self.alert} ADD 1 {alert} 1 {amcp_quote(payload)}"]
        return []
