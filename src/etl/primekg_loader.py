"""
ETL module for loading PrimeKG data into Neo4j.
"""
import os
import sys
import logging
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import DATA_DIR
from src.db.neo4j_connector import get_connector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PrimeKGLoader:
    """
    Loader class for importing PrimeKG data into Neo4j.
    """
    
    def __init__(self, batch_size=1000):
        """
        Initialize the PrimeKG loader.
        
        Args:
            batch_size (int): Number of records to process in a batch
        """
        self.db = get_connector()
        self.batch_size = batch_size
        self.node_types = set()
        self.relation_types = set()
        
    def analyze_data(self, csv_file):
        """
        Analyze the PrimeKG data to extract node and relationship types.
        
        Args:
            csv_file (str): Path to the PrimeKG CSV file
            
        Returns:
            dict: Analysis results
        """
        logger.info(f"Analyzing PrimeKG data from {csv_file}")
        
        # Read the CSV file in chunks to handle large files
        node_types = set()
        relation_types = set()
        node_sources = set()
        total_rows = 0
        
        # Get file size for progress bar
        file_size = os.path.getsize(csv_file)
        
        # Create a progress bar
        with tqdm(total=file_size, unit='B', unit_scale=True, desc="Analyzing data") as pbar:
            for chunk in pd.read_csv(csv_file, chunksize=self.batch_size):
                total_rows += len(chunk)
                
                # Extract unique node types
                node_types.update(chunk['x_type'].unique())
                node_types.update(chunk['y_type'].unique())
                
                # Extract unique relation types
                relation_types.update(chunk['relation'].unique())
                
                # Extract unique node sources
                node_sources.update(chunk['x_source'].unique())
                node_sources.update(chunk['y_source'].unique())
                
                # Update progress bar with approximate chunk size (rows * avg bytes per row)
                chunk_size = len(chunk) * 100  # Approximate bytes per row
                pbar.update(chunk_size)
                pbar.set_postfix({"rows": f"{total_rows:,}", "node_types": len(node_types), "rel_types": len(relation_types)})
        
        # Store the results
        self.node_types = node_types
        self.relation_types = relation_types
        
        # Convert node types to Neo4j-friendly format
        neo4j_node_types = [self._normalize_label(node_type) for node_type in node_types]
        
        # Log the results
        logger.info(f"Found {len(node_types)} node types: {', '.join(node_types)}")
        logger.info(f"Found {len(relation_types)} relation types")
        logger.info(f"Found {len(node_sources)} node sources: {', '.join(node_sources)}")
        logger.info(f"Total rows: {total_rows}")
        
        return {
            "node_types": list(node_types),
            "neo4j_node_types": neo4j_node_types,
            "relation_types": list(relation_types),
            "node_sources": list(node_sources),
            "total_rows": total_rows
        }
    
    def _normalize_label(self, label):
        """
        Normalize a label for Neo4j (remove spaces, slashes, etc.)
        
        Args:
            label (str): Original label
            
        Returns:
            str: Normalized label
        """
        # Replace slashes with underscores
        normalized = label.replace('/', '_')
        # Replace spaces with underscores
        normalized = normalized.replace(' ', '_')
        # Capitalize the first letter
        normalized = normalized.capitalize()
        
        return normalized
    
    def create_constraints(self):
        """
        Create necessary constraints in Neo4j for efficient data loading.
        """
        logger.info("Creating constraints in Neo4j...")
        
        # Create constraints for node uniqueness based on discovered node types
        constraints = []
        
        # If we've analyzed the data, use the discovered node types
        if self.node_types:
            for node_type in self.node_types:
                neo4j_label = self._normalize_label(node_type)
                constraints.append(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{neo4j_label}) REQUIRE n.id IS UNIQUE")
        else:
            # Default constraints if we haven't analyzed the data yet
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Gene_protein) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Disease) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Drug) REQUIRE n.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Pathway) REQUIRE n.id IS UNIQUE"
            ]
        
        for constraint in constraints:
            result = self.db.execute_write_query(constraint)
            if not result.get("success", False):
                logger.error(f"Failed to create constraint: {constraint}")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        logger.info("Constraints created successfully")
    
    def extract_and_load_nodes(self, edges_file):
        """
        Extract unique nodes from the edges file and load them into Neo4j.
        
        Args:
            edges_file (str): Path to the edges CSV file
            
        Returns:
            int: Number of nodes loaded
        """
        logger.info(f"Extracting and loading nodes from {edges_file}")
        
        if not os.path.exists(edges_file):
            logger.error(f"Edges file not found: {edges_file}")
            return 0
        
        # First, analyze the data if we haven't already
        if not self.node_types:
            self.analyze_data(edges_file)
        
        # Create constraints
        self.create_constraints()
        
        # Track unique nodes to avoid duplicates
        processed_nodes = set()
        total_nodes = 0
        chunk_count = 0
        total_rows_processed = 0
        
        # Get file size for progress bar
        file_size = os.path.getsize(edges_file)
        
        # Setup progress bar with file size as total
        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc="Extracting nodes")
        
        # Process the file in chunks
        for chunk in pd.read_csv(edges_file, chunksize=self.batch_size):
            # Extract source nodes (x)
            source_nodes = []
            for _, row in chunk.iterrows():
                node_id = f"{row['x_type']}_{row['x_id']}"
                if node_id not in processed_nodes:
                    processed_nodes.add(node_id)
                    # Always store IDs as strings to avoid integer overflow issues
                    node_id_value = str(row['x_id'])
                    
                    source_nodes.append({
                        'id': node_id_value,
                        'name': row['x_name'],
                        'type': row['x_type'],
                        'source': row['x_source']
                    })
            
            # Extract target nodes (y)
            target_nodes = []
            for _, row in chunk.iterrows():
                node_id = f"{row['y_type']}_{row['y_id']}"
                if node_id not in processed_nodes:
                    processed_nodes.add(node_id)
                    # Always store IDs as strings to avoid integer overflow issues
                    node_id_value = str(row['y_id'])
                    
                    target_nodes.append({
                        'id': node_id_value,
                        'name': row['y_name'],
                        'type': row['y_type'],
                        'source': row['y_source']
                    })
            
            # Load source nodes
            if source_nodes:
                new_nodes = self._load_nodes_batch(source_nodes)
                total_nodes += new_nodes
                pbar.update(new_nodes)
            
            # Load target nodes
            if target_nodes:
                new_nodes = self._load_nodes_batch(target_nodes)
                total_nodes += new_nodes
                pbar.update(new_nodes)
            
            # Update progress information
            chunk_count += 1
            total_rows_processed += len(chunk)
            
            # Update progress bar with approximate chunk size (rows * avg bytes per row)
            chunk_size = len(chunk) * 100  # Approximate bytes per row
            pbar.update(chunk_size)
            
            # Update progress bar description with stats
            pbar.set_postfix({"rows": f"{total_rows_processed:,}", "nodes": f"{total_nodes:,}", "unique": len(processed_nodes)})
        
        # Close progress bar
        pbar.close()
        logger.info(f"Loaded {total_nodes:,} unique nodes into Neo4j from {total_rows_processed:,} rows")
        return total_nodes
    
    def _load_nodes_batch(self, nodes):
        """
        Load a batch of nodes into Neo4j.
        
        Args:
            nodes (list): List of node dictionaries
            
        Returns:
            int: Number of nodes loaded
        """
        total_loaded = 0
        
        for node in nodes:
            # Convert node type to a valid Neo4j label
            node_label = self._normalize_label(node['type'])
            
            # Create a Cypher query to create the node
            query = f"""
            MERGE (n:{node_label} {{id: $id}})
            SET n.name = $name, n.type = $type, n.source = $source
            """
            
            result = self.db.execute_write_query(query, {
                'id': node['id'],
                'name': node['name'],
                'type': node['type'],
                'source': node['source']
            })
            
            if result.get("success", False):
                total_loaded += result.get("nodes_created", 0)
            else:
                logger.error(f"Failed to create node: {node['id']}")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        return total_loaded
    
    def load_relationships(self, edges_file):
        """
        Load relationships from the PrimeKG CSV file into Neo4j.
        
        Args:
            edges_file (str): Path to the PrimeKG CSV file
            
        Returns:
            int: Number of relationships loaded
        """
        logger.info(f"Loading relationships from {edges_file}")
        
        if not os.path.exists(edges_file):
            logger.error(f"Edges file not found: {edges_file}")
            return 0
        
        # First, analyze the data if we haven't already
        if not self.relation_types:
            self.analyze_data(edges_file)
        
        # Track progress
        total_relationships = 0
        processed_rows = 0
        chunk_count = 0
        
        # Get file size for progress bar
        file_size = os.path.getsize(edges_file)
        
        # Setup progress bar with file size as total
        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc="Loading relationships")
        
        # Process the file in chunks
        for chunk in pd.read_csv(edges_file, chunksize=self.batch_size):
            # Process each relationship in the chunk and collect results
            chunk_results = []
            for _, row in chunk.iterrows():
                # Normalize the relationship type for Neo4j
                relation_type = row['relation'].replace(' ', '_').upper()
                
                # Create source and target node labels
                source_label = self._normalize_label(row['x_type'])
                target_label = self._normalize_label(row['y_type'])
                
                # Create a Cypher query to create the relationship
                query = f"""
                MATCH (source:{source_label} {{id: $source_id}})
                MATCH (target:{target_label} {{id: $target_id}})
                MERGE (source)-[r:{relation_type}]->(target)
                SET r.display_relation = $display_relation
                """
                
                # Always store IDs as strings to avoid integer overflow issues
                source_id_value = str(row['x_id'])
                target_id_value = str(row['y_id'])
                
                result = self.db.execute_write_query(query, {
                    'source_id': source_id_value,
                    'target_id': target_id_value,
                    'display_relation': row['display_relation']
                })
                
                # Add result to list for later processing
                chunk_results.append(result)
                
                if not result.get("success", False):
                    logger.error(f"Failed to create relationship: {row['x_id']} -> {row['y_id']}")
                    logger.error(f"Error: {result.get('error', 'Unknown error')}")
            
            # Update progress
            processed_rows += len(chunk)
            chunk_count += 1
            
            # Count new relationships in this chunk
            chunk_relationships = 0
            for result in chunk_results:
                if result.get("success", False):
                    new_rels = result.get("relationships_created", 0)
                    chunk_relationships += new_rels
                    total_relationships += new_rels
            
            # Update progress bar with approximate chunk size (rows * avg bytes per row)
            chunk_size = len(chunk) * 100  # Approximate bytes per row
            pbar.update(chunk_size)
            
            # Update progress bar with stats
            pbar.set_postfix({"rows": f"{processed_rows:,}", "rels": f"{total_relationships:,}", "chunks": chunk_count})
        
        # Close progress bar
        pbar.close()
        logger.info(f"Loaded {total_relationships:,} relationships into Neo4j from {processed_rows:,} rows")
        return total_relationships
    
    def load_primekg_data(self, edges_file=None):
        """
        Load PrimeKG data into Neo4j.
        
        Args:
            edges_file (str): Path to the PrimeKG CSV file
            
        Returns:
            dict: Summary of the loading process
        """
        # Default file path if not provided
        if edges_file is None:
            edges_file = os.path.join(DATA_DIR, "primekg_data.csv")
        
        # Analyze the data
        analysis = self.analyze_data(edges_file)
        
        # Create constraints
        self.create_constraints()
        
        # Extract and load nodes
        nodes_count = self.extract_and_load_nodes(edges_file)
        
        # Load relationships
        relationships_count = self.load_relationships(edges_file)
        
        return {
            "nodes_loaded": nodes_count,
            "relationships_loaded": relationships_count,
            "node_types": len(self.node_types),
            "relation_types": len(self.relation_types),
            "total_rows_processed": analysis["total_rows"]
        }


def main():
    """Main function to load PrimeKG data into Neo4j."""
    loader = PrimeKGLoader()
    result = loader.load_primekg_data()
    logger.info(f"Loading complete: {result}")


if __name__ == "__main__":
    main()
