"""
Utility functions for the PrimeKG to Neo4j server.
"""
import os
import logging
import pandas as pd
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_directory(directory: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def read_csv_in_chunks(file_path: str, chunk_size: int = 10000) -> pd.DataFrame:
    """
    Read a CSV file in chunks to handle large files.
    
    Args:
        file_path: Path to the CSV file
        chunk_size: Number of rows to read at a time
        
    Yields:
        DataFrame chunks
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    try:
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            yield chunk
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")

def analyze_csv_structure(file_path: str) -> Dict[str, Any]:
    """
    Analyze the structure of a CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Dict with structure information
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {}
    
    try:
        # Read just the header and a few rows
        df = pd.read_csv(file_path, nrows=5)
        
        # Get column information
        columns = list(df.columns)
        dtypes = {col: str(df[col].dtype) for col in columns}
        
        # Get file size
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        
        # Count total rows (this reads the whole file)
        total_rows = sum(1 for _ in open(file_path)) - 1  # Subtract header row
        
        return {
            "file_path": file_path,
            "file_size_mb": round(file_size, 2),
            "total_rows": total_rows,
            "columns": columns,
            "column_dtypes": dtypes,
            "sample_data": df.to_dict(orient="records")
        }
    except Exception as e:
        logger.error(f"Error analyzing CSV file: {e}")
        return {}

def format_cypher_properties(properties: Dict[str, Any]) -> str:
    """
    Format a dictionary of properties for use in a Cypher query.
    
    Args:
        properties: Dictionary of properties
        
    Returns:
        Formatted string for Cypher query
    """
    props = []
    for key, value in properties.items():
        if isinstance(value, str):
            # Escape single quotes in strings
            escaped_value = value.replace("'", "\\'")
            props.append(f"{key}: '{escaped_value}'")
        elif isinstance(value, (int, float, bool)):
            props.append(f"{key}: {value}")
        elif value is None:
            props.append(f"{key}: null")
        else:
            # Skip complex types
            continue
    
    return "{" + ", ".join(props) + "}"

def get_node_categories(nodes_file: str) -> List[str]:
    """
    Get a list of unique node categories from a nodes CSV file.
    
    Args:
        nodes_file: Path to the nodes CSV file
        
    Returns:
        List of unique categories
    """
    if not os.path.exists(nodes_file):
        logger.error(f"Nodes file not found: {nodes_file}")
        return []
    
    try:
        # Read just the category column
        df = pd.read_csv(nodes_file, usecols=["category"])
        categories = df["category"].unique().tolist()
        return categories
    except Exception as e:
        logger.error(f"Error reading node categories: {e}")
        return []

def get_edge_types(edges_file: str) -> List[str]:
    """
    Get a list of unique edge types from an edges CSV file.
    
    Args:
        edges_file: Path to the edges CSV file
        
    Returns:
        List of unique edge types
    """
    if not os.path.exists(edges_file):
        logger.error(f"Edges file not found: {edges_file}")
        return []
    
    try:
        # Read just the relation column
        df = pd.read_csv(edges_file, usecols=["relation"])
        relations = df["relation"].unique().tolist()
        return relations
    except Exception as e:
        logger.error(f"Error reading edge types: {e}")
        return []
