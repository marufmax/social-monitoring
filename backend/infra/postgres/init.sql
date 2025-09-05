-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create main database user
-- (This is handled by docker environment variables)

-- Initial schema will be created by SQLAlchemy migrations

---