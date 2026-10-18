"""Resilient TCP client: keeps one connection to the engine, reconnects with
backoff, and re-syncs the full state after every (re)connection."""
import asyncio
import logging
import socket
import time

log = logging.getLogger("tcp")


class EngineClient:
    def __init__(self, host, port, terminator: bytes, on_connect=None):
        self.host, self.port, self.terminator = host, port, terminator
        self.on_connect = on_connect
        self.writer: asyncio.StreamWriter | None = None
        self.connected = asyncio.Event()
        self.last_sent = 0.0

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
                log.info("connected to %s:%s", self.host, self.port)
                if self.on_connect:
                    await self.on_connect()
                await self._read_replies(reader)
            except OSError as e:
                log.warning("connection error: %s", e)
            self.connected.clear()
            log.info("disconnected, retrying in %ss", delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def _read_replies(self, reader: asyncio.StreamReader):
        """AMCP replies start with a 3-digit code: 2xx ok, 4xx bad command, 5xx server error."""
        while line := await reader.readline():
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            code = text[:3]
            rtt = (time.perf_counter() - self.last_sent) * 1000
            if code.isdigit() and code[0] in "45":
                log.error("engine error: %s", text)
            elif code.isdigit():
                log.debug("engine ok: %s (%.1f ms)", text, rtt)

    async def send(self, cmd: str) -> bool:
        if not self.connected.is_set() or self.writer is None:
            log.warning("offline, dropped: %s", cmd)
            return False
        try:
            self.writer.write(cmd.encode("utf-8") + self.terminator)
            await self.writer.drain()
        except OSError as e:
            log.warning("send failed: %s", e)
            return False
        self.last_sent = time.perf_counter()
        log.info(">> %s", cmd)
        return True
