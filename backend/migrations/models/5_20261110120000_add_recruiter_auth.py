from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recruiters" ADD "password_hash" VARCHAR(255);
        ALTER TABLE "recruiters" ADD "is_demo" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "recruiters" DROP COLUMN "password_hash";
        ALTER TABLE "recruiters" DROP COLUMN "is_demo";"""


MODELS_STATE = (
    "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"
    "nXgeXl/5+LEAw="
)
