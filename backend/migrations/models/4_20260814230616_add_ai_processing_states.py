from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "applications" ADD "evaluation_processing_state" VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED';
        ALTER TABLE "jobs" ADD "criteria_processing_state" VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED';
        ALTER TABLE "resumes" ADD "processing_state" VARCHAR(20) NOT NULL DEFAULT 'NOT_STARTED';
        UPDATE "applications" SET "evaluation_processing_state" = 'COMPLETED'
        WHERE EXISTS (
            SELECT 1 FROM "ai_evaluations"
            WHERE "ai_evaluations"."application_id" = "applications"."id"
        );
        UPDATE "jobs" SET "criteria_processing_state" = 'COMPLETED'
        WHERE "evaluation_criteria" <> '{}'::JSONB
          AND "evaluation_criteria" <> '[]'::JSONB;
        UPDATE "resumes" SET "processing_state" = 'COMPLETED'
        WHERE NULLIF(BTRIM("raw_text"), '') IS NOT NULL
          AND "parsed_data" <> '{}'::JSONB
          AND "parsed_data" <> '[]'::JSONB;
        COMMENT ON COLUMN "applications"."evaluation_processing_state" IS 'NOT_STARTED: NOT_STARTED\nPROCESSING: PROCESSING\nCOMPLETED: COMPLETED\nFAILED: FAILED';
COMMENT ON COLUMN "jobs"."criteria_processing_state" IS 'NOT_STARTED: NOT_STARTED\nPROCESSING: PROCESSING\nCOMPLETED: COMPLETED\nFAILED: FAILED';
COMMENT ON COLUMN "resumes"."processing_state" IS 'NOT_STARTED: NOT_STARTED\nPROCESSING: PROCESSING\nCOMPLETED: COMPLETED\nFAILED: FAILED';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "jobs" DROP COLUMN "criteria_processing_state";
        ALTER TABLE "resumes" DROP COLUMN "processing_state";
        ALTER TABLE "applications" DROP COLUMN "evaluation_processing_state";"""


MODELS_STATE = (
    "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"
)
