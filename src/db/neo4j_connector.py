"""
Neo4j database connector for the PrimeKG project.
"""
import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

# Import configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Neo4jConnector:
    """
    A connector class for Neo4j database operations.
    """
    
    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD):
        """
        Initialize the Neo4j connector.
        
        Args:
            uri (str): Neo4j connection URI
            user (str): Neo4j username
            password (str): Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        
    def connect(self):
        """
        Establish a connection to the Neo4j database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connection by running a simple query
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            logger.info(f"Connected to Neo4j database at {self.uri}")
            return True
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
        except AuthError as e:
            logger.error(f"Authentication error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def execute_query(self, query, parameters=None):
        """
        Execute a Cypher query.
        
        Args:
            query (str): Cypher query to execute
            parameters (dict): Query parameters
            
        Returns:
            list: Query results
        """
        if not self.driver:
            if not self.connect():
                logger.error("Cannot execute query: Not connected to Neo4j")
                return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            return []
    
    def execute_write_query(self, query, parameters=None):
        """
        Execute a write query (CREATE, MERGE, DELETE, etc.).
        
        Args:
            query (str): Cypher query to execute
            parameters (dict): Query parameters
            
        Returns:
            dict: Summary statistics
        """
        if not self.driver:
            if not self.connect():
                logger.error("Cannot execute query: Not connected to Neo4j")
                return {"success": False, "error": "Not connected to Neo4j"}
        
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                summary = result.consume()
                return {
                    "success": True,
                    "nodes_created": summary.counters.nodes_created,
                    "relationships_created": summary.counters.relationships_created,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_deleted": summary.counters.relationships_deleted
                }
        except Exception as e:
            logger.error(f"Write query execution error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            return {"success": False, "error": str(e)}

# Singleton instance
_connector = None

def get_connector():
    """
    Get a singleton instance of the Neo4j connector.
    
    Returns:
        Neo4jConnector: A Neo4j connector instance
    """
    global _connector
    if _connector is None:
        _connector = Neo4jConnector()
    return _connector
