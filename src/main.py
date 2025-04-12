"""
Main entry point for the PrimeKG to Neo4j project.
"""
import os
import sys
import argparse
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DATA_DIR
from src.db.neo4j_connector import get_connector
from src.etl.primekg_loader import PrimeKGLoader

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='PrimeKG to Neo4j')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Download data command
    download_parser = subparsers.add_parser('download', help='Download PrimeKG data')
    download_parser.add_argument('--output-dir', default=DATA_DIR, help='Directory to save data to')
    
    # Load data command
    load_parser = subparsers.add_parser('load', help='Load PrimeKG data into Neo4j')
    load_parser.add_argument('--data-file', help='Path to PrimeKG CSV data file')
    load_parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for loading data')
    
    # Query data command
    query_parser = subparsers.add_parser('query', help='Run a Cypher query against Neo4j')
    query_parser.add_argument('--query', required=True, help='Cypher query to execute')
    query_parser.add_argument('--params', help='Query parameters in JSON format')
    
    # Test connection command
    test_parser = subparsers.add_parser('test-connection', help='Test Neo4j connection')
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.command == 'download':
        # Import the download function here to avoid circular imports
        from scripts.download_data import download_primekg_data
        download_primekg_data(output_dir=args.output_dir)
    
    elif args.command == 'load':
        # Load PrimeKG data into Neo4j
        loader = PrimeKGLoader(batch_size=args.batch_size)
        result = loader.load_primekg_data(edges_file=args.data_file)
        logger.info(f"Loading complete: {result}")
    
    elif args.command == 'query':
        # Run a Cypher query
        import json
        db = get_connector()
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in params argument")
                sys.exit(1)
        
        result = db.execute_query(args.query, params)
        print(json.dumps(result, indent=2, default=str))
    
    elif args.command == 'test-connection':
        # Test Neo4j connection
        db = get_connector()
        if db.connect():
            logger.info("Neo4j connection successful")
        else:
            logger.error("Neo4j connection failed")
            sys.exit(1)
    
    else:
        # No command specified, show help
        logger.error("No command specified")
        parse_args()  # This will print the help message

if __name__ == "__main__":
    main()
