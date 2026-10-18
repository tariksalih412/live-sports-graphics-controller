"""All settings come from environment variables, so the same code runs at home and on a server."""
import os

ENGINE = os.getenv("ENGINE", "caspar")                 # caspar | viz
ENGINE_HOST = os.getenv("ENGINE_HOST", "127.0.0.1")
ENGINE_PORT = int(os.getenv("ENGINE_PORT", "5250" if ENGINE == "caspar" else "6100"))

FEED = os.getenv("FEED", "replay")                     # replay | live
REPLAY_DIR = os.getenv("REPLAY_DIR", "tools/recordings")
API_KEY = os.getenv("API_KEY", "")
FIXTURE_ID = int(os.getenv("FIXTURE_ID", "0"))

# Replay can run fast; for a live API keep this high enough to respect your daily quota
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))

# CasparCG channel/layers
CASPAR_CHANNEL = int(os.getenv("CASPAR_CHANNEL", "1"))
SCOREBUG_LAYER = int(os.getenv("SCOREBUG_LAYER", "20"))
ALERT_LAYER = int(os.getenv("ALERT_LAYER", "21"))

# Where CasparCG loads templates from:
#   empty  -> by name from CasparCG's own template folder ("scorebug")
#   a URL  -> served over HTTP, e.g. http://127.0.0.1:8088/  (python -m http.server 8088 --directory templates)
TEMPLATE_BASE = os.getenv("TEMPLATE_BASE", "")
