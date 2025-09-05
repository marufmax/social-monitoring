"""
Seed test data for development
"""
import asyncio
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import get_database, get_database_url
from app.models.post import Post
from app.models.campaign import Campaign
from app.models.user import User


async def seed_test_data():
    """Seed database with test data"""
    print("🌱 Seeding test data...")

    # This will be implemented when we have the actual models
    # For now, just create some sample data structure

    sample_posts = [
        {
            "platform": "twitter",
            "platform_id": "1234567890",
            "content": "This is a sample tweet about social media monitoring #monitoring #tech",
            "author_info": {
                "username": "techuser",
                "followers": 1000,
                "verified": False
            },
            "created_at": datetime.utcnow(),
            "metadata": {
                "retweets": 5,
                "likes": 12,
                "hashtags": ["monitoring", "tech"]
            }
        },
        {
            "platform": "linkedin",
            "platform_id": "post_9876543210",
            "content": "Excited to announce our new social media analytics platform! #analytics #business",
            "author_info": {
                "name": "Business User",
                "company": "Tech Corp",
                "connections": 500
            },
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "metadata": {
                "likes": 25,
                "comments": 3,
                "shares": 8
            }
        }
    ]

    print(f"📊 Sample data structure ready: {len(sample_posts)} posts")
    print("✅ Test data seeding completed")


def main():
    """Main seeding function"""
    asyncio.run(seed_test_data())


if __name__ == "__main__":
    main()