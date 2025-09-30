# src/database_connector.py
import os
import pandas as pd
import sqlalchemy
import sys

# Add the project root to the path to import settings
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.append(project_root)

from config.settings import get_settings

def get_database_engine():
    """
    Creates and returns a SQLAlchemy engine connected to the main CFDI database.
    Uses the centralized settings to get the correct database URL (PostgreSQL or SQLite).
    """
    try:
        settings = get_settings()
        database_url = settings.DATABASE_URL
        
        print(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else database_url}")
        
        engine = sqlalchemy.create_engine(
            database_url,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600    # Recycle connections every hour
        )
        return engine
    except Exception as e:
        print(f"❌ ERROR: Failed to create database engine: {e}")
        return None

def get_approved_skus_df():
    """
    Fetches all approved SKUs from the database and returns them as a pandas DataFrame
    with cleaned, lowercase column names.
    """
    print("Connecting to the database to fetch approved SKus...")
    engine = get_database_engine()
    if engine is None:
        return pd.DataFrame() # Return empty dataframe on failure

    try:
        with engine.connect() as connection:
            approved_skus_df = pd.read_sql_table('approved_skus', connection)
            
            # Clean and standardize column names
            approved_skus_df.columns = approved_skus_df.columns.str.lower().str.strip()
            
            print(f"✅ Successfully fetched and cleaned {len(approved_skus_df)} approved SKUs.")
            return approved_skus_df
    except Exception as e:
        print(f"❌ ERROR: Failed to fetch approved SKUs: {e}")
        return pd.DataFrame()



