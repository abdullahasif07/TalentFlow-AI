from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "application_notes" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "content" TEXT NOT NULL,
    "application_id" INT NOT NULL REFERENCES "applications" ("id") ON DELETE CASCADE,
    "recruiter_id" INT REFERENCES "recruiters" ("id") ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS "idx_application_applica_a5bfb5" ON "application_notes" ("application_id", "created_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "application_notes";"""


MODELS_STATE = (
    "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"
    "f9TYYHcHUqcyj35tTsNC7vOrA8/g8W7mmu"
)
