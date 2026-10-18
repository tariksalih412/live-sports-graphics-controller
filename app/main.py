import asyncio
import logging
import statistics
import time

import aiohttp

from . import config
from .feed import LiveFeed, ReplayFeed
from .formatters import get_formatter
from .state import diff
from .transport import EngineClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-5s %(name)s: %(message)s")
log = logging.getLogger("main")


async def main():
    fmt = get_formatter()
    current = {"state": None}
    timings: list[float] = []

    async def resync():
        if current["state"] is not None:
            log.info("re-sync after (re)connect")
            for cmd in fmt.render("full_sync", current["state"]):
                await engine.send(cmd)

    engine = EngineClient(config.ENGINE_HOST, config.ENGINE_PORT, fmt.terminator, on_connect=resync)
    asyncio.create_task(engine.run())
    try:                                           # give the engine a moment before the first snapshot
        await asyncio.wait_for(engine.connected.wait(), timeout=5)
    except asyncio.TimeoutError:
        log.warning("engine not reachable yet; will re-sync when it connects")

    async with aiohttp.ClientSession() as session:
        feed = (LiveFeed(session, config.API_KEY, config.FIXTURE_ID)
                if config.FEED == "live" else ReplayFeed(config.REPLAY_DIR))
        log.info("engine=%s feed=%s interval=%ss", config.ENGINE, config.FEED, config.POLL_INTERVAL)

        while True:
            t0 = time.perf_counter()
            try:
                new = await feed.fetch()
            except Exception as e:                 # a bad response never stops the service
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
                log.info("changes=%s fetch=%.1fms processing=%.2fms",
                         [k for k, _ in changes], (t_fetched - t0) * 1000, proc_ms)
                if len(timings) >= 2:
                    log.info("processing avg=%.2fms max=%.2fms",
                             statistics.mean(timings), max(timings))

            await asyncio.sleep(max(0, config.POLL_INTERVAL - (time.perf_counter() - t0)))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
