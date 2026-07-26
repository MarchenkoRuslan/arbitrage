import asyncio

from loguru import logger

from src.core.config import Settings
from src.core.state import MarketState
from src.exchanges.hyperliquid import HyperliquidConnector
from src.exchanges.lighter import LighterConnector
from src.output.console import print_opportunities
from src.screener.finder import find_opportunities_from_state


class App:
    """Application orchestrator — manages lifecycle and coordination."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.state = MarketState(sample_interval_s=self.settings.loop_interval_s)
        self.hl = HyperliquidConnector(self.settings)
        self.lighter = LighterConnector(self.settings)

    async def poll_once(self) -> None:
        """Single poll cycle: fetch from both DEXes, update state, run screener."""
        hl_rates_tickers, lighter_rates_tickers = await asyncio.gather(
            self.hl.get_market_data(),
            self.lighter.get_market_data(),
        )
        hl_rates, hl_tickers = hl_rates_tickers
        lighter_rates, lighter_tickers = lighter_rates_tickers

        await asyncio.gather(
            self.state.update_funding("hyperliquid", hl_rates),
            self.state.update_tickers("hyperliquid", hl_tickers),
            self.state.update_funding("lighter", lighter_rates),
            self.state.update_tickers("lighter", lighter_tickers),
        )

        common = set(hl_rates) & set(lighter_rates)
        logger.info(
            "State updated: HL={} Lighter={} | Common={}",
            len(hl_rates), len(lighter_rates), len(common),
        )

        opps = find_opportunities_from_state(self.state, self.settings)
        print_opportunities(opps)

        if not opps:
            logger.info(
                "No opportunities above {:.1f} bps edge threshold",
                self.settings.min_score_bps,
            )

    async def run_loop(self) -> None:
        """Continuous polling loop."""
        logger.info(
            "Starting DEX screener (interval={}s, min_edge={:.1f}bps, min_vol={:.0f})",
            self.settings.loop_interval_s,
            self.settings.min_score_bps,
            self.settings.min_volume_24h,
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
        await asyncio.gather(self.hl.close(), self.lighter.close(), return_exceptions=True)
