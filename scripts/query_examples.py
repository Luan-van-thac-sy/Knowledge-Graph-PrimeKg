"""
Example queries for the PrimeKG Neo4j database.
"""
import os
import sys
import json
import logging
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.neo4j_connector import get_connector

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_results(results: List[Dict[str, Any]], limit: int = 10) -> None:
    """
    Print query results in a readable format.
    
    Args:
        results: List of result records
        limit: Maximum number of results to print
    """
    if not results:
        print("No results found.")
        return
    
    print(f"Found {len(results)} results. Showing first {min(limit, len(results))}:")
    for i, record in enumerate(results[:limit]):
        print(f"\nResult {i+1}:")
        print(json.dumps(record, indent=2, default=str))
    
    if len(results) > limit:
        print(f"\n... and {len(results) - limit} more results.")

def example_queries():
    """Run example queries against the Neo4j database."""
    db = get_connector()
    if not db.connect():
        logger.error("Failed to connect to Neo4j database")
        return
    
    print("\n=== Example 1: Get all node categories ===")
    query = """
    CALL db.labels() YIELD label
    RETURN label
    ORDER BY label
    """
    results = db.execute_query(query)
    print_results(results)
    
    print("\n=== Example 2: Count nodes by category ===")
    query = """
    MATCH (n)
    RETURN labels(n)[0] AS category, count(*) AS count
    ORDER BY count DESC
    """
    results = db.execute_query(query)
    print_results(results)
    
    print("\n=== Example 3: Count relationships by type ===")
    query = """
    MATCH ()-[r]->()
    RETURN type(r) AS relationship_type, count(*) AS count
    ORDER BY count DESC
    """
    results = db.execute_query(query)
    print_results(results)
    
    print("\n=== Example 4: Find diseases related to a specific gene ===")
    query = """
    MATCH (g:Gene {name: $gene_name})-[r]-(d:Disease)
    RETURN d.id AS disease_id, d.name AS disease_name, type(r) AS relationship_type
    LIMIT 10
    """
    results = db.execute_query(query, {"gene_name": "TP53"})
    print_results(results)
    
    print("\n=== Example 5: Find drugs that target a specific disease ===")
    query = """
    MATCH (drug:Drug)-[r]-(disease:Disease {name: $disease_name})
    RETURN drug.id AS drug_id, drug.name AS drug_name, type(r) AS relationship_type
    LIMIT 10
    """
    results = db.execute_query(query, {"disease_name": "Alzheimer's disease"})
    print_results(results)
    
    print("\n=== Example 6: Find the shortest path between two nodes ===")
    query = """
    MATCH (start:Gene {name: $start_name}),
          (end:Disease {name: $end_name}),
          path = shortestPath((start)-[*]-(end))
    RETURN [node in nodes(path) | node.name] AS node_names,
           [type(rel) in relationships(path)] AS relationship_types,
           length(path) AS path_length
    """
    results = db.execute_query(query, {
        "start_name": "APOE",
        "end_name": "Alzheimer's disease"
    })
    print_results(results)
    
    print("\n=== Example 7: Find common pathways between two genes ===")
    query = """
    MATCH (g1:Gene {name: $gene1_name})-[r1]-(p:Pathway)-[r2]-(g2:Gene {name: $gene2_name})
    RETURN p.id AS pathway_id, p.name AS pathway_name
    """
    results = db.execute_query(query, {
        "gene1_name": "APOE",
        "gene2_name": "APP"
    })
    print_results(results)
    
    print("\n=== Example 8: Find proteins that interact with a specific gene ===")
    query = """
    MATCH (g:Gene {name: $gene_name})-[r:INTERACTS_WITH]-(p:Protein)
    RETURN p.id AS protein_id, p.name AS protein_name
    LIMIT 10
    """
    results = db.execute_query(query, {"gene_name": "BRCA1"})
    print_results(results)
    
    print("\n=== Example 9: Find biological processes associated with a disease ===")
    query = """
    MATCH (d:Disease {name: $disease_name})-[*1..2]-(bp:Biological_Process)
    RETURN bp.id AS process_id, bp.name AS process_name
    LIMIT 10
    """
    results = db.execute_query(query, {"disease_name": "Type 2 diabetes mellitus"})
    print_results(results)
    
    print("\n=== Example 10: Find side effects of drugs used for a specific disease ===")
    query = """
    MATCH (d:Disease {name: $disease_name})-[]-(drug:Drug)-[]-(se:SideEffect)
    RETURN drug.name AS drug_name, se.name AS side_effect
    LIMIT 20
    """
    results = db.execute_query(query, {"disease_name": "Hypertension"})
    print_results(results)

if __name__ == "__main__":
    example_queries()
