"""Fake engine for testing without CasparCG/Viz.
  python tools/mock_engine.py            -> CasparCG mode, port 5250, replies "202 OK"
  python tools/mock_engine.py viz 6100   -> Viz mode, null-terminated, no replies
"""
import asyncio
import sys
import time

MODE = sys.argv[1] if len(sys.argv) > 1 else "caspar"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else (5250 if MODE == "caspar" else 6100)
SEP = b"\r\n" if MODE == "caspar" else b"\0"


async def handle(reader, writer):
    print("client connected:", writer.get_extra_info("peername"))
    buf = b""
    while data := await reader.read(4096):
        buf += data
        while SEP in buf:
            msg, buf = buf.split(SEP, 1)
            print(f"{time.time():.3f}  RX: {msg.decode('utf-8', 'replace')}")
            if MODE == "caspar":
                writer.write(b"202 OK\r\n")
                await writer.drain()
    print("client disconnected")


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", PORT)
    print(f"mock {MODE} engine listening on {PORT}")
    async with server:
        await server.serve_forever()

asyncio.run(main())
