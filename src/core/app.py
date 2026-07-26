import asyncio

from loguru import logger

from src.core.config import Settings
from src.core.state import MarketState
from src.exchanges.hyperliquid import HyperliquidConnector
from src.exchanges.lighter import LighterConnector
from src.output.console import print_opportunities
from src.screener.finder import find_opportunities_from_state
from src.screener.validator import validate_opportunities


class App:
    """Application orchestrator — manages lifecycle and coordination."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.state = MarketState(sample_interval_s=self.settings.loop_interval_s)
        self.hl = HyperliquidConnector(self.settings)
        self.lighter = LighterConnector(self.settings)

    async def poll_once(self) -> None:
        """Single poll cycle: fetch from both DEXes, update state, run screener."""
        fetch_timeout = self.settings.http_timeout * (self.settings.http_max_retries + 1) + 5
        try:
            results = await asyncio.wait_for(
                asyncio.gather(
                    self.hl.get_market_data(),
                    self.lighter.get_market_data(),
                    return_exceptions=True,
                ),
                timeout=fetch_timeout,
            )
        except TimeoutError:
            logger.error("Poll fetch timed out after {:.0f}s, skipping cycle", fetch_timeout)
            return

        hl_rates: dict = {}
        hl_tickers: dict = {}
        lighter_rates: dict = {}
        lighter_tickers: dict = {}

        if isinstance(results[0], Exception):
            logger.warning("Hyperliquid fetch failed: {}", results[0])
        else:
            hl_rates, hl_tickers = results[0]

        if isinstance(results[1], Exception):
            logger.warning("Lighter fetch failed: {}", results[1])
        else:
            lighter_rates, lighter_tickers = results[1]

        if not hl_rates and not lighter_rates:
            logger.error("Both exchanges failed, skipping poll cycle")
            return

        update_tasks = []
        if hl_rates:
            update_tasks.append(self.state.update_funding("hyperliquid", hl_rates))
            update_tasks.append(self.state.update_tickers("hyperliquid", hl_tickers))
        if lighter_rates:
            update_tasks.append(self.state.update_funding("lighter", lighter_rates))
            update_tasks.append(self.state.update_tickers("lighter", lighter_tickers))
        await asyncio.gather(*update_tasks)

        # Record paired snapshots only for symbols where both exchanges have data
        common = set(hl_rates) & set(lighter_rates)
        for symbol in common:
            self.state.record_snapshot(symbol, hl_rates[symbol], lighter_rates[symbol])

        logger.info(
            "State updated: HL={} Lighter={} | Common={}",
            len(hl_rates), len(lighter_rates), len(common),
        )

        opps = find_opportunities_from_state(self.state, self.settings)
        validated = validate_opportunities(opps, self.state, self.settings)
        print_opportunities(validated)

        ready_count = sum(1 for v in validated if v.status == "ready")
        if not validated:
            logger.info(
                "No opportunities above {:.1f} bps edge threshold",
                self.settings.min_score_bps,
            )
        elif ready_count == 0:
            logger.info("Found {} opportunities, none ready for entry", len(validated))

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
