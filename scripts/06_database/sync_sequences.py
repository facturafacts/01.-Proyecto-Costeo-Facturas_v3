import os
import sys
from pathlib import Path
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
project_root = Path(__file__).parent.parent.parent

def sync_sequences():
    """Synchronizes all PostgreSQL sequences with the max ID of their respective tables."""
    load_dotenv(dotenv_path=project_root / '.env')
    database_url = os.getenv("DATABASE_URL")

    if not database_url or "sqlite" in database_url:
        logger.error("❌ This script is for PostgreSQL only. DATABASE_URL must be set correctly.")
        sys.exit(1)

    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            logger.info("✅ Connected to the PostgreSQL database.")
            
            # This query gets the name of every sequence in the public schema
            get_sequences_sql = text("""
                SELECT c.relname AS sequence_name
                FROM pg_class c
                WHERE c.relkind = 'S' AND c.relnamespace = (
                    SELECT oid FROM pg_namespace WHERE nspname = 'public'
                );
            """)
            
            sequences = connection.execute(get_sequences_sql).fetchall()
            
            if not sequences:
                logger.warning("No sequences found to update.")
                return

            logger.info(f"Found {len(sequences)} sequences to synchronize...")
            
            for seq in sequences:
                sequence_name = seq[0]
                # The table name is usually the sequence name minus the "_id_seq" suffix
                table_name = sequence_name.replace('_id_seq', '')
                
                try:
                    # This command updates the sequence counter to the max value of the ID column
                    sync_sql = text(f"SELECT setval('{sequence_name}', (SELECT MAX(id) FROM {table_name}));")
                    connection.execute(sync_sql)
                    logger.info(f"  -> Synchronized sequence '{sequence_name}' for table '{table_name}'.")
                except Exception as e:
                    logger.error(f"  -> Could not sync sequence '{sequence_name}'. Does table '{table_name}' exist? Error: {e}")
            
            # A commit is needed for setval to take effect across sessions
            connection.commit()
            logger.info("✅ All sequences synchronized successfully!")

    except Exception as e:
        logger.error(f"❌ An error occurred during sequence synchronization: {e}")

if __name__ == "__main__":
    sync_sequences() 