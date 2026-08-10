from tortoise import Tortoise

from app.config import TORTOISE_ORM


async def init_db() -> None:
    """Initialize ORM connections. Schema changes are managed by Aerich."""

    await Tortoise.init(config=TORTOISE_ORM)


async def close_db() -> None:
    await Tortoise.close_connections()

