#!/usr/bin/env python3
"""
Database migration script
"""
import asyncio
import os
from sqlalchemy import create_engine
from app.database import Base, get_database_url
from app.models import *  # Import all models


async def create_tables():
    """Create all database tables"""
    database_url = get_database_url()
    engine = create_engine(database_url)

    print("🗄️  Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def main():
    """Main migration function"""
    asyncio.run(create_tables())


if __name__ == "__main__":
    main()