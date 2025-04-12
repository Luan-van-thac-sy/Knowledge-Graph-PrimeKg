"""
Script to download PrimeKG data from Harvard Dataverse.
"""
import os
import sys
import requests
from tqdm import tqdm
import zipfile
import pandas as pd

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import DATA_DIR, PRIMEKG_DATA_URL

def ensure_data_dir():
    """Ensure the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Data directory: {DATA_DIR}")

def download_file(url, destination):
    """
    Download a file from a URL with progress bar.
    
    Args:
        url (str): URL to download from
        destination (str): Path to save the file
    """
    if os.path.exists(destination):
        print(f"File already exists: {destination}")
        return

    print(f"Downloading from {url} to {destination}")
    response = requests.get(url, stream=True)
    
    if response.status_code != 200:
        print(f"Failed to download: {response.status_code}")
        return
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    
    with open(destination, 'wb') as file, tqdm(
            desc=os.path.basename(destination),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
        for data in response.iter_content(block_size):
            size = file.write(data)
            bar.update(size)
    
    print(f"Download complete: {destination}")

def extract_zip(zip_path, extract_to):
    """
    Extract a zip file.
    
    Args:
        zip_path (str): Path to the zip file
        extract_to (str): Directory to extract to
    """
    if not os.path.exists(zip_path):
        print(f"Zip file not found: {zip_path}")
        return
    
    print(f"Extracting {zip_path} to {extract_to}")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    print(f"Extraction complete: {extract_to}")

def download_primekg_data(output_dir=None):
    """Download PrimeKG data from Harvard Dataverse.
    
    Args:
        output_dir (str): Directory to save data to. If None, uses DATA_DIR from config.
    """
    # Use provided output_dir or default to DATA_DIR
    data_dir = output_dir or DATA_DIR
    
    # Ensure the data directory exists
    os.makedirs(data_dir, exist_ok=True)
    print(f"Data directory: {data_dir}")
    
    # Download the data - directly as CSV
    csv_path = os.path.join(data_dir, "primekg_data.csv")
    download_file(PRIMEKG_DATA_URL, csv_path)
    print(f"Download complete: {csv_path}")
    
    # Check if the file exists and has content
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        file_size = os.path.getsize(csv_path) / (1024 * 1024)  # Size in MB
        print(f"\nDownloaded file: primekg_data.csv ({file_size:.2f} MB)")
        
        # Print a preview of the file structure
        try:
            df = pd.read_csv(csv_path, nrows=5)
            print(f"Columns: {', '.join(df.columns)}")
            print(f"Sample rows: {len(df)}")
            
            # Analyze the data structure
            print("\nData Structure:")
            for col in df.columns:
                print(f"  - {col}: {df[col].dtype}")
                
            # Count unique values for categorical columns
            for col in df.columns:
                if df[col].dtype == 'object' and len(df[col].unique()) < 20:
                    print(f"\nUnique values for {col}:")
                    print(df[col].value_counts().head())
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"Error: Downloaded file is empty or does not exist")

if __name__ == "__main__":
    download_primekg_data()
