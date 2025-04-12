"""
Script to initialize the Neo4j database for PrimeKG data.
"""
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.neo4j_connector import get_connector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the Neo4j database with constraints and indexes."""
    logger.info("Initializing Neo4j database...")
    
    db = get_connector()
    if not db.connect():
        logger.error("Failed to connect to Neo4j database")
        return False
    
    # Create constraints for node uniqueness
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Disease) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Gene) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Protein) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Drug) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Pathway) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Anatomy) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Symptom) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:SideEffect) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Biological_Process) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Cellular_Component) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Molecular_Function) REQUIRE n.id IS UNIQUE"
    ]
    
    # Create indexes for better query performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (n:Disease) ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Gene) ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Protein) ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Drug) ON (n.name)"
    ]
    
    # Execute constraint queries
    for constraint in constraints:
        logger.info(f"Creating constraint: {constraint}")
        result = db.execute_write_query(constraint)
        if not result.get("success", False):
            logger.error(f"Failed to create constraint: {constraint}")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
    
    # Execute index queries
    for index in indexes:
        logger.info(f"Creating index: {index}")
        result = db.execute_write_query(index)
        if not result.get("success", False):
            logger.error(f"Failed to create index: {index}")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
    
    logger.info("Database initialization complete")
    return True

if __name__ == "__main__":
    init_database()
