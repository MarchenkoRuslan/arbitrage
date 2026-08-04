import argparse
import asyncio

import uvicorn

from src.api.server import create_api
from src.core.app import App
from src.core.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="DEX Funding Rate Arbitrage Screener")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--serve", action="store_true", help="Start REST API server with polling loop")
    group.add_argument("--loop", action="store_true", help="Run continuous polling with console output")
    args = parser.parse_args()

    settings = Settings()
    app = App(settings)

    if args.serve:
        fastapi_app = create_api(app)
        uvicorn.run(fastapi_app, host=settings.api_host, port=settings.api_port)
    elif args.loop:
        asyncio.run(app.run_loop())
    else:
        asyncio.run(app.run_single())


if __name__ == "__main__":
    main()
