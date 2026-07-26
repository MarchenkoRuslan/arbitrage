import asyncio
import sys

from loguru import logger

from src.core.config import settings
from src.exchanges.aster import AsterConnector
from src.exchanges.hyperliquid import HyperliquidConnector
from src.screener.finder import find_opportunities


async def run_once() -> None:
    hl = HyperliquidConnector()
    aster = AsterConnector()

    try:
        hl_rates, aster_rates, hl_tickers, aster_tickers = await asyncio.gather(
            hl.get_funding_rates(),
            aster.get_funding_rates(),
            hl.get_tickers(),
            aster.get_tickers(),
        )

        logger.info(
            "Fetched rates: HL={} Aster={} | Common symbols: {}",
            len(hl_rates),
            len(aster_rates),
            len(set(hl_rates) & set(aster_rates)),
        )

        opps = find_opportunities(hl_rates, aster_rates, hl_tickers, aster_tickers)

        if not opps:
            logger.info("No opportunities above {:.1f}% APR threshold", settings.min_score_apr)
            return

        # Print header
        header = f"{'Symbol':<10} {'Long':<12} {'Short':<12} {'Diff APR%':>10} {'Basis bps':>10} {'Score%':>8}"
        print("\n" + header)
        print("-" * len(header))

        for opp in opps[:20]:
            print(
                f"{opp.symbol:<10} {opp.long_exchange:<12} {opp.short_exchange:<12} "
                f"{opp.funding_diff_apr:>10.2f} {opp.basis_bps:>10.2f} {opp.combined_score:>8.2f}"
            )

        print(f"\nTotal opportunities: {len(opps)}")

    finally:
        await hl.close()
        await aster.close()


async def run_loop() -> None:
    logger.info("Starting screener loop (interval={}s)", settings.loop_interval_s)
    while True:
        try:
            await run_once()
        except Exception as e:
            logger.error("Screener error: {}", e)
        await asyncio.sleep(settings.loop_interval_s)


def main() -> None:
    loop = "--loop" in sys.argv
    if loop:
        asyncio.run(run_loop())
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
