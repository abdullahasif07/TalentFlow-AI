"""Create the demo company, logins, and sample data.

Safe to run repeatedly: accounts are updated in place and demo data is only inserted
when the company has no jobs yet. Use ``python -m scripts.reset_demo --yes`` to
replace existing data with a fresh copy.
"""

import asyncio

from tortoise import Tortoise

from app.config import TORTOISE_ORM
from app.demo.seed import ensure_accounts, ensure_company, populate_demo_data


async def seed() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        company = await ensure_company()
        for line in await ensure_accounts(company):
            print(line)
        summary = await populate_demo_data(company)
        print(summary.describe())
        if not summary.created:
            print("To replace existing data with the demo dataset: python -m scripts.reset_demo --yes")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())
