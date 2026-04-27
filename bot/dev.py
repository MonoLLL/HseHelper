import asyncio
from pathlib import Path

from watchfiles import run_process

from main import main


def run_bot():
    asyncio.run(main())


if __name__ == "__main__":
    run_process(str(Path(__file__).resolve().parent), target=run_bot)
