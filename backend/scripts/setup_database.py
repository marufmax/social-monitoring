#!/usr/bin/env python3
"""Database setup and maintenance script."""

import asyncio
from pathlib import Path
from sqlalchemy import create_engine, text
from app.config import get_settings


async def setup_indexes():
    """Apply performance indexes."""
    settings = get_settings()
    engine = create_engine(settings.database_url)

    indexes_dir = Path(__file__).parent.parent / "infra" / "postgres" / "indexes"

    # Apply indexes in order
    index_files = [
        "02_performance_indexes.sql",
    ]

    with engine.connect() as conn:
        for file_name in index_files:
            file_path = indexes_dir / file_name
            if file_path.exists():
                print(f"Applying {file_name}...")
                sql_content = file_path.read_text()
                conn.execute(text(sql_content))
                conn.commit()
                print(f"✓ {file_name} applied successfully")


if __name__ == "__main__":
    asyncio.run(setup_indexes())
