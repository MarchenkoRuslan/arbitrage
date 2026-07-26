import asyncio

from loguru import logger

from src.core.config import Settings
from src.core.state import PollCache
from src.exchanges.vooi import VooiConnector
from src.output.console import print_opportunities
from src.screener.finder import filter_opportunities


class App:
    """Application orchestrator — manages lifecycle and coordination."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.cache = PollCache()
        self.vooi = VooiConnector(self.settings)

    async def poll_once(self) -> None:
        """Single poll cycle: fetch opportunities from VOOI, filter, and display."""
        raw_opps = await self.vooi.get_opportunities()
        self.cache.update(raw_opps)

        logger.info("Fetched {} raw opportunities from VOOI", len(raw_opps))

        opps = filter_opportunities(raw_opps, self.settings)
        print_opportunities(opps)

        if not opps:
            logger.info(
                "No opportunities above {:.1%} net APR with vol >= {:.0f}",
                self.settings.min_net_apr,
                self.settings.min_volume_24h,
            )

    async def run_loop(self) -> None:
        """Continuous polling loop."""
        logger.info(
            "Starting DEX screener (interval={}s, min_net_apr={:.1%}, min_vol={:.0f}, exchanges={})",
            self.settings.loop_interval_s,
            self.settings.min_net_apr,
            self.settings.min_volume_24h,
            self.settings.vooi_target_exchanges,
        )
        try:
            while True:
                try:
                    await self.poll_once()
                except Exception as e:
                    logger.error("Poll error: {}", e)
                await asyncio.sleep(self.settings.loop_interval_s)
        finally:
            await self.shutdown()

    async def run_single(self) -> None:
        """Single execution then shutdown."""
        try:
            await self.poll_once()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        """Graceful shutdown — close all connections."""
        logger.debug("Shutting down...")
        await self.vooi.close()
