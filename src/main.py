import asyncio
import sys

from src.core.app import App
from src.core.config import Settings


def main() -> None:
    settings = Settings()
    app = App(settings)

    if "--loop" in sys.argv:
        asyncio.run(app.run_loop())
    else:
        asyncio.run(app.run_single())


if __name__ == "__main__":
    main()
