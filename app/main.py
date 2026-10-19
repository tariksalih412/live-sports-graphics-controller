"""Live Sports Graphics Controller: football data in, CasparCG graphics out."""
import asyncio
import logging
import statistics
import time
from pathlib import Path

import aiohttp

from . import config
from .feed import LiveFeed, ReplayFeed
from .formatters import CasparFormatter
from .state import diff
from .transport import EngineClient

VERSION = "1.0.0"


def setup_logging():
    fmt = logging.Formatter("%(asctime)s %(levelname)-5s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    if config.LOG_FILE:
        Path(config.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)


log = logging.getLogger("main")


async def main():
    fmt = CasparFormatter()
    current = {"state": None}
    timings: list[float] = []

    async def resync():
        if current["state"] is not None:
            log.info("re-sync after (re)connect")
            for cmd in fmt.render("full_sync", current["state"]):
                await engine.send(cmd)

    engine = EngineClient(config.ENGINE_HOST, config.ENGINE_PORT, fmt.terminator, on_connect=resync)
    asyncio.create_task(engine.run())
    try:                                           # give CasparCG a moment before the first snapshot
        await asyncio.wait_for(engine.connected.wait(), timeout=5)
    except asyncio.TimeoutError:
        log.warning("CasparCG not reachable yet; will re-sync when it connects")

    async with aiohttp.ClientSession() as session:
        feed = (LiveFeed(session, config.API_KEY, config.FIXTURE_ID)
                if config.FEED == "live" else ReplayFeed(config.REPLAY_DIR))
        log.info("sports-gfx %s | CasparCG %s:%s | feed=%s %s | interval=%ss",
                 VERSION, config.ENGINE_HOST, config.ENGINE_PORT, config.FEED,
                 config.REPLAY_DIR if config.FEED == "replay" else config.FIXTURE_ID,
                 config.POLL_INTERVAL)
        try:
            while True:
                t0 = time.perf_counter()
                try:
                    new = await feed.fetch()
                except Exception as e:             # a bad response never stops the service
                    log.error("feed error: %s", e)
                    await asyncio.sleep(config.POLL_INTERVAL)
                    continue
                t_fetched = time.perf_counter()

                changes = diff(current["state"], new)
                for kind, data in changes:
                    for cmd in fmt.render(kind, data):
                        await engine.send(cmd)
                current["state"] = new

                if changes:
                    proc_ms = (time.perf_counter() - t_fetched) * 1000
                    timings.append(proc_ms)
                    log.info("%s %s' %d-%d changes=%s fetch=%.1fms processing=%.2fms",
                             new.status, new.minute if new.minute is not None else "-",
                             new.home_score, new.away_score, [k for k, _ in changes],
                             (t_fetched - t0) * 1000, proc_ms)

                await asyncio.sleep(max(0, config.POLL_INTERVAL - (time.perf_counter() - t0)))
        finally:
            if timings:
                ordered = sorted(timings)
                p95 = ordered[max(0, int(len(ordered) * 0.95) - 1)]
                log.info("SUMMARY change sets=%d processing avg=%.2fms p95=%.2fms max=%.2fms",
                         len(timings), statistics.mean(timings), p95, max(timings))


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
