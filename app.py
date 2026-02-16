import asyncio

from bot import run_bot
from storage import init_db


def main():
    init_db()
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
