from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.api import auth_router, resumes_router
from app.config import settings
from app.db import close_db, init_db
from app.graphql.context import get_graphql_context
from app.graphql.schema import schema


logger = logging.getLogger(__name__)
DEV_SESSION_SECRET = "dev-only-insecure-session-secret-change-me"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.session_secret.get_secret_value() == DEV_SESSION_SECRET:
        if settings.is_production:
            raise RuntimeError("Set SESSION_SECRET before running in production.")
        logger.warning("Using the development SESSION_SECRET; set one before deploying.")
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(
    GraphQLRouter(
        schema,
        context_getter=get_graphql_context,
        multipart_uploads_enabled=True,
        graphql_ide="graphiql" if settings.graphql_ide else None,
    ),
    prefix="/graphql",
)
app.include_router(auth_router)
app.include_router(resumes_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}
