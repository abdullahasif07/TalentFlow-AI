from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE INDEX IF NOT EXISTS "idx_application_job_id_def4dc" ON "applications" ("job_id", "applied_at");
        CREATE INDEX IF NOT EXISTS "idx_application_applica_feadcb" ON "application_status_history" ("application_id", "created_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_application_applica_feadcb";
        DROP INDEX IF EXISTS "idx_application_job_id_def4dc";"""


MODELS_STATE = (
    "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"
)
