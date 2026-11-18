from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    # Demo sandboxes are copies of the same company, so names can repeat. The unique
    # constraint is found by column rather than by name in case Postgres named it
    # differently.
    return """
        DO $$
        DECLARE constraint_name TEXT;
        BEGIN
            SELECT con.conname INTO constraint_name
            FROM pg_constraint con
            JOIN pg_attribute att
              ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey)
            WHERE con.conrelid = '"companies"'::regclass
              AND con.contype = 'u'
              AND att.attname = 'name'
              AND array_length(con.conkey, 1) = 1;
            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE "companies" DROP CONSTRAINT %I', constraint_name);
            END IF;
        END $$;
        ALTER TABLE "companies" ADD "is_sandbox" BOOL NOT NULL DEFAULT False;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "companies" DROP COLUMN "is_sandbox";
        ALTER TABLE "companies" ADD CONSTRAINT "companies_name_key" UNIQUE ("name");"""


MODELS_STATE = (
    "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"
    "9grFoZIyhtVLpXv7xvx/L8f4f/fi8="
)
