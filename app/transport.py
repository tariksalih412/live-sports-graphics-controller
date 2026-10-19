"""Resilient TCP client for CasparCG's AMCP port: keeps one connection, reconnects
with backoff (capped at 5 s), and re-syncs the full state after every (re)connection."""
import asyncio
import logging
import socket
import time

log = logging.getLogger("tcp")
MAX_BACKOFF = 5


class EngineClient:
    def __init__(self, host, port, terminator: bytes, on_connect=None):
        self.host, self.port, self.terminator = host, port, terminator
        self.on_connect = on_connect
        self.writer: asyncio.StreamWriter | None = None
        self.connected = asyncio.Event()
        self.down_since: float | None = None

    async def run(self):
        delay = 1
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                sock = writer.get_extra_info("socket")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.writer, delay = writer, 1
                self.connected.set()
                if self.down_since is not None:
                    log.info("reconnected to %s:%s after %.1fs offline",
                             self.host, self.port, time.perf_counter() - self.down_since)
                else:
                    log.info("connected to %s:%s", self.host, self.port)
                self.down_since = None
                if self.on_connect:
                    await self.on_connect()
                await self._read_replies(reader)
            except OSError as e:
                log.warning("connection error: %s", e)
            if self.connected.is_set() or self.down_since is None:
                self.down_since = time.perf_counter()
            self.connected.clear()
            log.info("engine offline, retrying in %ss", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_BACKOFF)

    async def _read_replies(self, reader: asyncio.StreamReader):
        """AMCP replies start with a 3-digit code: 2xx ok, 4xx bad command, 5xx server error."""
        while line := await reader.readline():
            text = line.decode("utf-8", "replace").strip()
            code = text[:3]
            if code.isdigit() and code[0] in "45":
                log.error("CasparCG error: %s", text)

    async def send(self, cmd: str) -> bool:
        if not self.connected.is_set() or self.writer is None:
            log.warning("offline, dropped: %s", cmd[:80])
            return False
        try:
            self.writer.write(cmd.encode("utf-8") + self.terminator)
            await self.writer.drain()
        except OSError as e:
            log.warning("send failed: %s", e)
            return False
        log.info(">> %s", cmd)
        return True
