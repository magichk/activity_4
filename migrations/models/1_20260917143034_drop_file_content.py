from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    # IF EXISTS: si la app ya arranco antes con GENERATE_SCHEMAS=true, la tabla se crea
    # directamente a partir de los modelos actuales (ya sin "content"), y esta migracion
    # no tendria nada que borrar. Sin el IF EXISTS, aerich fallaria en ese caso.
    return """
        ALTER TABLE "files" DROP COLUMN IF EXISTS "content";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "files" ADD COLUMN IF NOT EXISTS "content" BYTEA;"""
