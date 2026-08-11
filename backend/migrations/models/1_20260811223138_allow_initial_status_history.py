from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "application_status_history" ALTER COLUMN "previous_status" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE "application_status_history"
        SET "previous_status" = "new_status"
        WHERE "previous_status" IS NULL;
        ALTER TABLE "application_status_history" ALTER COLUMN "previous_status" SET NOT NULL;"""


MODELS_STATE = (
    "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"
    "=="
)
