import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .logger import logger

# Define the database file path relative to the p62 folder
db_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sales_data_fixed.db')
DATABASE_URL = f"sqlite:///{db_file_path}"

try:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info(f"Database engine created successfully for: {db_file_path}")
except Exception as e:
    logger.critical(f"Failed to create database engine: {e}")
    raise

def get_db():
    """Provides a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 