"""Wipe all applicants and the demo company's jobs, then reseed the demo dataset.

This deletes data. It requires DEMO_MODE=true and the --yes flag.
"""

import argparse
import asyncio

from tortoise import Tortoise

from app.config import TORTOISE_ORM
from app.demo.seed import reset_demo_data


async def main() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        summary = await reset_demo_data()
        print(f"Demo reset complete. {summary.describe()}")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Confirm deleting existing data.")
    if not parser.parse_args().yes:
        parser.error("This deletes all applicants. Re-run with --yes to confirm.")
    asyncio.run(main())
