"""Type AMCP commands by hand and see CasparCG's reply.
  python tools/amcp_console.py [host] [port]
Try:  VERSION
      INFO
      PLAY 1-10 RED
      CLEAR 1-10
"""
import socket
import sys

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 5250

with socket.create_connection((host, port), timeout=5) as s:
    print(f"connected to {host}:{port} — empty line to quit")
    while (cmd := input("AMCP> ").strip()):
        s.sendall(cmd.encode("utf-8") + b"\r\n")
        try:
            print(s.recv(65536).decode("utf-8", "replace").rstrip())
        except socket.timeout:
            print("(no reply)")
