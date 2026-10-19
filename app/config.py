"""All settings come from environment variables, so the same code runs at home and on a server."""
import os

# CasparCG AMCP server
ENGINE_HOST = os.getenv("ENGINE_HOST", "127.0.0.1")
ENGINE_PORT = int(os.getenv("ENGINE_PORT", "5250"))
CASPAR_CHANNEL = int(os.getenv("CASPAR_CHANNEL", "1"))
SCOREBUG_LAYER = int(os.getenv("SCOREBUG_LAYER", "20"))
ALERT_LAYER = int(os.getenv("ALERT_LAYER", "21"))

# Where CasparCG loads templates from:
#   empty  -> by name from CasparCG's own template folder ("scorebug")
#   a URL  -> served over HTTP, e.g. http://127.0.0.1:8088/  (python -m http.server 8088 --directory templates)
TEMPLATE_BASE = os.getenv("TEMPLATE_BASE", "")

# Data source
FEED = os.getenv("FEED", "replay")                     # replay | live
REPLAY_DIR = os.getenv("REPLAY_DIR", "tools/recordings")
API_KEY = os.getenv("API_KEY", "")
FIXTURE_ID = int(os.getenv("FIXTURE_ID", "0"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "2"))  # seconds; keep it high in live mode (daily quota)

# Logging: console + file
LOG_FILE = os.getenv("LOG_FILE", "logs/sports-gfx.log")
