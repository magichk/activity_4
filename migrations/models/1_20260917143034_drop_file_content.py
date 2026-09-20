from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "files" DROP COLUMN "content";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "files" ADD "content" BYTEA;"""
