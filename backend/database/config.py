"""
Database configuration and connection management for the Dengue Agents API.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Get database connection details from environment variables
DB_USER = os.getenv("POSTGRESQL_USERNAME", "chathistory")
DB_PASSWORD = os.getenv("POSTGRESQL_PASSWORD", "ChatHistory87b!")
DB_NAME = os.getenv("POSTGRESQL_DB", "chat-history")
DB_HOST = os.getenv("POSTGRESQL_ROUTE", "postgresql.chat-history.svc.cluster.local")
DB_PORT = os.getenv("POSTGRESQL_PORT", "5432")

# Check if we should use in-memory SQLite for local testing
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

# SQLAlchemy database URL
if USE_SQLITE:
    logger.info("Using SQLite in-memory database for local testing")
    DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    logger.info(f"Using PostgreSQL database at {DB_HOST}:{DB_PORT}")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db():
    """
    Get a database session that will be closed after use.
    Designed to be used with FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize the database schema.
    This creates all tables if they don't exist.
    """
    try:
        # Import models to ensure they're registered with the Base class
        from .models import User, Session, Message, AgentTransition

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def check_db_connection() -> bool:
    """
    Check if the database connection is working.
    Returns True if connection successful, False otherwise.
    """
    try:
        # Make a simple query to test the connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return False
