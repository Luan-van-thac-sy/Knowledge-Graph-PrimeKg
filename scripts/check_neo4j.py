"""
Script to check if Neo4j is running and provide setup instructions if needed.
"""
import os
import sys
import logging
import requests
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_neo4j_running():
    """
    Check if Neo4j is running and accessible.
    
    Returns:
        bool: True if Neo4j is running, False otherwise
    """
    try:
        # Try to connect to Neo4j
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            result.single()
        driver.close()
        
        logger.info(f"Neo4j is running at {NEO4J_URI}")
        return True
    except ServiceUnavailable:
        logger.error(f"Neo4j is not running at {NEO4J_URI}")
        return False
    except AuthError:
        logger.error(f"Authentication error: Check your Neo4j credentials")
        return False
    except Exception as e:
        logger.error(f"Error connecting to Neo4j: {e}")
        return False

def check_neo4j_browser():
    """
    Check if Neo4j Browser is accessible.
    
    Returns:
        bool: True if Neo4j Browser is accessible, False otherwise
    """
    # Extract host and port from NEO4J_URI
    # Example: bolt://localhost:7687 -> http://localhost:7474
    try:
        parts = NEO4J_URI.split("://")[1].split(":")
        host = parts[0]
        browser_url = f"http://{host}:7474"
        
        response = requests.get(browser_url, timeout=5)
        if response.status_code == 200:
            logger.info(f"Neo4j Browser is accessible at {browser_url}")
            return True
        else:
            logger.error(f"Neo4j Browser returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error checking Neo4j Browser: {e}")
        return False

def print_setup_instructions():
    """Print instructions for setting up Neo4j."""
    print("\n" + "="*80)
    print("Neo4j Setup Instructions")
    print("="*80)
    print("\nNeo4j is not running or not accessible. Follow these steps to set it up:")
    
    print("\n1. Install Neo4j:")
    print("   - macOS (using Homebrew): brew install neo4j")
    print("   - Docker: docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest")
    
    print("\n2. Start Neo4j:")
    print("   - macOS (Homebrew): brew services start neo4j")
    print("   - Docker: Already running if you used the command above")
    
    print("\n3. Configure Neo4j:")
    print("   - Open Neo4j Browser at http://localhost:7474")
    print("   - Default credentials: neo4j/neo4j")
    print("   - You'll be prompted to change the password on first login")
    
    print("\n4. Update .env file:")
    print("   - Copy .env.example to .env: cp .env.example .env")
    print("   - Update NEO4J_PASSWORD in .env with your new password")
    
    print("\n5. Verify connection:")
    print("   - Run this script again: python scripts/check_neo4j.py")
    
    print("\n" + "="*80)

def main():
    """Main function to check Neo4j status."""
    neo4j_running = check_neo4j_running()
    
    if neo4j_running:
        # If Neo4j is running, check if Browser is accessible
        browser_accessible = check_neo4j_browser()
        
        if browser_accessible:
            print("\nNeo4j is running and the Browser is accessible.")
            print("You're ready to load PrimeKG data into Neo4j!")
            print("\nNext steps:")
            print("1. Run: python -m src.main load")
            print("2. After loading, explore the data in Neo4j Browser")
        else:
            print("\nNeo4j is running, but the Browser might not be accessible.")
            print("You can still load data, but you might not be able to visualize it in the Browser.")
            print("\nTo load data, run: python -m src.main load")
    else:
        # If Neo4j is not running, print setup instructions
        print_setup_instructions()

if __name__ == "__main__":
    main()
