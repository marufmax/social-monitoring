#!/usr/bin/env python3
"""
Development setup script for Social Media Monitor
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a shell command with error handling"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        sys.exit(1)


def main():
    """Main setup function"""
    print("🚀 Setting up Social Media Monitor development environment")

    # Check if Docker is running
    run_command("docker info", "Checking Docker status")

    # Create .env file from template if it doesn't exist
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        run_command("cp .env.example .env", "Creating .env file from template")
        print("📝 Please update .env file with your API keys")

    # Start development services
    run_command(
        "docker-compose -f docker-compose.dev.yml up -d",
        "Starting development services",
    )

    # Wait for services to be healthy
    print("⏳ Waiting for services to be ready...")
    run_command(
        "sleep 30",  # Give services time to start
        "Waiting for services",
    )

    # Create database tables (when we add migration scripts)
    # run_command("python scripts/migrate.py", "Running database migrations")

    # Seed test data (when we add seed scripts)
    # run_command("python scripts/seed_data.py", "Seeding test data")

    print("\n🎉 Development environment is ready!")
    print("\n📋 Available services:")
    print("   • PostgreSQL: localhost:5432")
    print("   • Redis: localhost:6379")
    print("   • RedisInsight: http://localhost:8001")
    print("   • SuperTokens: http://localhost:3567")
    print("\n🚀 To start the API server:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("\n🔧 To start collectors:")
    print("   python -m collectors.manager")
    print("\n📊 To start stream processor:")
    print("   python -m processor.main")


if __name__ == "__main__":
    main()
