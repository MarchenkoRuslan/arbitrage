import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from loguru import logger

from src.core.config import Settings
from src.core.models import ValidatedOpportunity
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
        self.started_at = datetime.now(timezone.utc)
        self.state = MarketState(sample_interval_s=self.settings.loop_interval_s)
        self.hl = HyperliquidConnector(self.settings)
        self.lighter = LighterConnector(self.settings)
        self.last_validated: list[ValidatedOpportunity] = []
        self.last_updated_at: datetime | None = None
        self.last_poll_started_at: datetime | None = None
        self.last_poll_finished_at: datetime | None = None
        self.last_poll_duration_ms: float | None = None
        self.poll_count_total = 0
        self.poll_count_success = 0
        self.poll_count_failed = 0
        self.exchange_last_ok: dict[str, bool | None] = {
            "hyperliquid": None,
            "lighter": None,
        }
        self._on_update: Callable[[list[ValidatedOpportunity]], Awaitable[None]] | None = None
        self._console_output: bool = True

    async def poll_once(self) -> None:
        """Single poll cycle: fetch from both DEXes, update state, run screener."""
        self.poll_count_total += 1
        self.last_poll_started_at = datetime.now(timezone.utc)
        poll_ok = False
        poll_cancelled = False
        fetch_timeout = self.settings.http_timeout * (self.settings.http_max_retries + 1) + 5
        try:
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
                # Global fetch timeout means neither venue can be trusted as fresh for this cycle.
                self.exchange_last_ok["hyperliquid"] = False
                self.exchange_last_ok["lighter"] = False
                logger.error("Poll fetch timed out after {:.0f}s, skipping cycle", fetch_timeout)
                return

            hl_rates: dict = {}
            hl_tickers: dict = {}
            lighter_rates: dict = {}
            lighter_tickers: dict = {}

            if isinstance(results[0], Exception):
                logger.warning("Hyperliquid fetch failed: {}", results[0])
                self.exchange_last_ok["hyperliquid"] = False
            else:
                hl_rates, hl_tickers = results[0]
                self.exchange_last_ok["hyperliquid"] = bool(hl_rates)

            if isinstance(results[1], Exception):
                logger.warning("Lighter fetch failed: {}", results[1])
                self.exchange_last_ok["lighter"] = False
            else:
                lighter_rates, lighter_tickers = results[1]
                self.exchange_last_ok["lighter"] = bool(lighter_rates)

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
                await self.state.record_snapshot(
                    symbol, {"hyperliquid": hl_rates[symbol], "lighter": lighter_rates[symbol]}
                )

            logger.info(
                "State updated: HL={} Lighter={} | Common={}",
                len(hl_rates), len(lighter_rates), len(common),
            )

            opps = find_opportunities_from_state(self.state, self.settings)
            validated = await validate_opportunities(opps, self.state, self.settings)
            self.last_validated = validated
            self.last_updated_at = datetime.now(timezone.utc)

            if self._console_output:
                print_opportunities(validated)
            if self._on_update is not None:
                await self._on_update(validated)

            ready_count = sum(1 for v in validated if v.status == "ready")
            if not validated:
                logger.info(
                    "No opportunities above {:.1f} bps edge threshold",
                    self.settings.min_score_bps,
                )
            elif ready_count == 0:
                logger.info("Found {} opportunities, none ready for entry", len(validated))

            poll_ok = True
        except asyncio.CancelledError:
            poll_cancelled = True
            raise
        finally:
            self.last_poll_finished_at = datetime.now(timezone.utc)
            self.last_poll_duration_ms = (
                self.last_poll_finished_at - self.last_poll_started_at
            ).total_seconds() * 1000
            if poll_cancelled:
                self.poll_count_total -= 1
            elif poll_ok:
                self.poll_count_success += 1
            else:
                self.poll_count_failed += 1

    async def run_loop(self, *, shutdown_on_exit: bool = True) -> None:
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
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("Poll error: {}", e)
                await asyncio.sleep(self.settings.loop_interval_s)
        finally:
            if shutdown_on_exit:
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
