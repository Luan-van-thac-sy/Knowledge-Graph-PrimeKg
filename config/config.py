"""
Configuration settings for the PrimeKG to Neo4j MCP server.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "Aq123456")

# PrimeKG data configuration
PRIMEKG_DATA_URL = "https://dataverse.harvard.edu/api/access/datafile/6180620"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PRIMEKG_NODES_FILE = os.path.join(DATA_DIR, "primekg_nodes.csv")
PRIMEKG_EDGES_FILE = os.path.join(DATA_DIR, "primekg_edges.csv")

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"
API_TITLE = "PrimeKG API"
API_DESCRIPTION = "API for accessing PrimeKG data from Neo4j"
API_VERSION = "0.1.0"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "app.log")
