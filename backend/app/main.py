from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.config import settings
from app.db import close_db, init_db
from app.graphql.schema import schema


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(
    title="TalentFlow AI API",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(GraphQLRouter(schema), prefix="/graphql")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
