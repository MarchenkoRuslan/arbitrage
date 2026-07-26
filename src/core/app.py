import asyncio

from loguru import logger

from src.core.config import Settings
from src.core.state import MarketState
from src.exchanges.aster import AsterConnector
from src.exchanges.hyperliquid import HyperliquidConnector
from src.output.console import print_opportunities
from src.screener.finder import find_opportunities_from_state


class App:
    """Application orchestrator — manages lifecycle and coordination."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.state = MarketState()
        self.hl = HyperliquidConnector(self.settings)
        self.aster = AsterConnector(self.settings)

    async def poll_once(self) -> None:
        """Single poll cycle: fetch data, update state, run screener."""
        hl_data, aster_rates, aster_tickers = await asyncio.gather(
            self.hl.get_market_data(),
            self.aster.get_funding_rates(),
            self.aster.get_tickers(),
        )
        hl_rates, hl_tickers = hl_data

        # Update shared state
        await asyncio.gather(
            self.state.update_funding("hyperliquid", hl_rates),
            self.state.update_tickers("hyperliquid", hl_tickers),
            self.state.update_funding("aster", aster_rates),
            self.state.update_tickers("aster", aster_tickers),
        )

        logger.info(
            "State updated: HL={} Aster={} | Common={}",
            len(hl_rates),
            len(aster_rates),
            len(set(hl_rates) & set(aster_rates)),
        )

        # Run screener from state (zero I/O hot path)
        opps = find_opportunities_from_state(self.state, self.settings)
        print_opportunities(opps)

        if not opps:
            logger.info("No opportunities above {:.1f}% APR threshold", self.settings.min_score_apr)

    async def run_loop(self) -> None:
        """Continuous polling loop."""
        logger.info(
            "Starting screener (interval={}s, hold={}h, min_score={}%)",
            self.settings.loop_interval_s,
            self.settings.expected_hold_hours,
            self.settings.min_score_apr,
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
        await asyncio.gather(
            self.hl.close(),
            self.aster.close(),
            return_exceptions=True,
        )
