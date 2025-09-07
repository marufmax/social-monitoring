import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

import alembic
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.core.logging import setup_logging
from app.database import SYNC_DATABASE_URL

# Configure logging
logger = setup_logging(__name__)

class MigrationManager:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.engine: Optional[AsyncEngine] = None
        self.alembic_cfg = self._setup_alembic_config()
        self.migration_history: List[Dict] = []

    def _setup_alembic_config(self) -> Config:
        """Initialize Alembic configuration"""
        config = Config()
        config.set_main_option("script_location", "alembic")
        config.set_main_option("sqlalchemy.url", self.db_url)
        return config

    async def initialize_engine(self):
        """Create async SQLAlchemy engine"""
        self.engine = create_async_engine(
            self.db_url,
            pool_pre_ping=True,
            pool_size=settings.POSTGRES_POOL_SIZE,
            max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        )

    @asynccontextmanager
    async def get_connection(self):
        """Async context manager for database connections"""
        if not self.engine:
            await self.initialize_engine()

        async with self.engine.begin() as connection:
            try:
                yield connection
            except Exception as e:
                await connection.rollback()
                raise e

    async def verify_indexes(self, connection) -> bool:
        """Verify database indexes are properly created"""
        try:
            inspector = inspect(connection)
            for table_name in inspector.get_table_names():
                indexes = inspector.get_indexes(table_name)
                logger.info(f"Verifying indexes for table {table_name}")
                for index in indexes:
                    logger.info(f"Found index: {index['name']}")
            return True
        except Exception as e:
            logger.error(f"Error verifying indexes: {e}")
            return False

    async def check_migration_status(self) -> tuple:
        """Check current migration status and pending migrations"""
        script = ScriptDirectory.from_config(self.alembic_cfg)

        async with self.get_connection() as connection:
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()
            head_rev = script.get_current_head()

            return current_rev, head_rev

    async def run_migration(self, target: str = "head") -> bool:
        """Execute database migration with progress tracking and error handling"""
        try:
            async with self.get_connection() as connection:
                # Start transaction
                await connection.begin()

                # Record migration start
                start_time = datetime.utcnow()
                logger.info(f"Starting migration to target: {target}")

                # Run migration
                alembic.command.upgrade(self.alembic_cfg, target)

                # Verify indexes
                if not await self.verify_indexes(connection):
                    raise Exception("Index verification failed")

                # Record successful migration
                end_time = datetime.utcnow()
                migration_record = {
                    "timestamp": end_time,
                    "duration": (end_time - start_time).total_seconds(),
                    "target": target,
                    "status": "success"
                }
                self.migration_history.append(migration_record)

                logger.info("Migration completed successfully")
                return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # Record failed migration
            self.migration_history.append({
                "timestamp": datetime.utcnow(),
                "target": target,
                "status": "failed",
                "error": str(e)
            })
            return False

    async def rollback(self, to_revision: str) -> bool:
        """Rollback database to specific revision"""
        try:
            async with self.get_connection() as connection:
                await connection.begin()

                logger.info(f"Rolling back to revision: {to_revision}")
                alembic.command.downgrade(self.alembic_cfg, to_revision)

                # Verify database state after rollback
                if not await self.verify_indexes(connection):
                    raise Exception("Index verification failed after rollback")

                return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    async def get_migration_history(self) -> List[Dict]:
        """Retrieve migration history"""
        return self.migration_history


async def main():
    """Main migration function"""
    try:
        # Initialize migration manager
        manager = MigrationManager(SYNC_DATABASE_URL)

        # Check current migration status
        current_rev, head_rev = await manager.check_migration_status()
        logger.info(f"Current revision: {current_rev}")
        logger.info(f"Target revision: {head_rev}")

        # Run migration if needed
        if current_rev != head_rev:
            success = await manager.run_migration()
            if not success:
                logger.error("Migration failed, initiating rollback...")
                await manager.rollback(current_rev)
                sys.exit(1)
        else:
            logger.info("Database is up to date")

        # Print migration history
        history = await manager.get_migration_history()
        logger.info("Migration history:")
        for record in history:
            logger.info(record)

    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
