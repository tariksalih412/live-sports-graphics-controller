"""Turn changes into engine commands. One class per engine; the rest of the
code never knows which engine is on the other end."""
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
        SCOREBUG, ALERT = tpl("scorebug"), tpl("event_alert")
        if kind == "full_sync":
            # ADD <cg_layer> <template> <play_on_load> <data>
            return [f"CG {self.bug} ADD 1 {SCOREBUG} 1 {amcp_quote(self._scorebug_data(data))}"]
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
                       "minute": g.minute, "score": f"{g.home_score} - {g.away_score}"}
            return [f"CG {self.alert} ADD 1 {ALERT} 1 {amcp_quote(payload)}"]
        if kind in ("yellow", "red"):
            e: Event = data
            payload = {"kind": kind, "player": e.player or "", "minute": e.minute}
            return [f"CG {self.alert} ADD 1 {ALERT} 1 {amcp_quote(payload)}"]
        return []


class VizFormatter:
    """For the second phase. Scene/container names must match your Viz scene;
    verify the exact command syntax against your Viz Engine version."""
    terminator = b"\0"

    def render(self, kind: str, data) -> list[str]:
        if kind in ("full_sync", "score"):
            cmds = [f"-1 RENDERER*TREE*$Score*GEOM*TEXT SET {data.home_score} - {data.away_score}"]
            if kind == "full_sync":
                cmds += [f"-1 RENDERER*TREE*$Home*GEOM*TEXT SET {data.home.name}",
                         f"-1 RENDERER*TREE*$Away*GEOM*TEXT SET {data.away.name}"]
            return cmds
        if kind == "goal":
            return ["-1 RENDERER*STAGE*DIRECTOR*GoalCelebration START"]
        return []


def get_formatter():
    return VizFormatter() if config.ENGINE == "viz" else CasparFormatter()
