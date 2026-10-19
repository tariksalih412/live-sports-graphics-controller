"""Check the two HTML templates on a running CasparCG, no typing needed.
  python tools/check_templates.py            (127.0.0.1:5250)
  python tools/check_templates.py 127.0.0.1 5260
Set TEMPLATE_BASE=http://127.0.0.1:8088/ to load templates over HTTP instead of the template folder.
Watch the CasparCG window while it runs.
"""
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.formatters import amcp_quote, tpl  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5250

STEPS = [
    ("Check connection", "VERSION", 1),
    ("Clear channel 1", "CLEAR 1", 1),
    ("Scorebug appears (0 - 0, minute 12)",
     "CG 1-20 ADD 1 " + tpl("scorebug") + " 1 " + amcp_quote(
         {"home": "السد", "away": "الدحيل", "homeScore": 0, "awayScore": 0, "minute": 12, "status": "1H"}), 3),
    ("Score changes to 1 - 0",
     "CG 1-20 UPDATE 1 " + amcp_quote({"homeScore": 1, "minute": 23}), 2),
    ("Goal alert (bottom, hides itself after 6s)",
     "CG 1-21 ADD 1 " + tpl("event_alert") + " 1 " + amcp_quote(
         {"kind": "goal", "team": "السد", "player": "أكرم عفيف", "minute": 23, "homeScore": 1, "awayScore": 0}), 8),
    ("Clock shows half time",
     "CG 1-20 UPDATE 1 " + amcp_quote({"minute": 45, "status": "HT"}), 3),
    ("Red card alert",
     "CG 1-21 ADD 1 " + tpl("event_alert") + " 1 " + amcp_quote(
         {"kind": "red", "player": "لوكاس أوكامبوس", "minute": 78}), 8),
    ("Scorebug leaves", "CG 1-20 STOP 1", 2),
    ("Clear everything", "CLEAR 1", 0),
]

with socket.create_connection((HOST, PORT), timeout=5) as s:
    print(f"connected to {HOST}:{PORT}\n")
    for i, (label, cmd, wait) in enumerate(STEPS, 1):
        print(f"[{i}/{len(STEPS)}] {label}")
        print(f"   >> {cmd}")
        s.sendall(cmd.encode("utf-8") + b"\r\n")
        try:
            reply = s.recv(65536).decode("utf-8", "replace").strip()
        except socket.timeout:
            reply = "(no reply)"
        flag = "OK " if reply[:1] == "2" else "!! "
        print(f"   {flag}{reply}\n")
        if reply[:1] in "45":
            print("Stopped: CasparCG rejected the command (see the reply above).")
            break
        time.sleep(wait)
print("done")
