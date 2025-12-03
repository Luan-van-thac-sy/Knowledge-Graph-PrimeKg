#!/bin/bash

# Script to setup and run Neo4j with udocker
# This script pulls Neo4j image, creates container, loads dump, and starts the database

set -e  # Exit on any error

echo "=========================================="
echo "Neo4j Setup with udocker"
echo "=========================================="

# Step 1: Pull the Neo4j image (with tag)
echo ""
echo "Step 1: Pulling Neo4j 5.14.0 image..."
udocker --allow-root pull neo4j:5.14.0

# Step 2: Create the container (use --name here)
echo ""
echo "Step 2: Creating container 'kg'..."
udocker --allow-root create --name=kg neo4j:5.14.0

# Step 3: Setup the container
echo ""
echo "Step 3: Setting up container execution mode..."
udocker --allow-root setup --execmode=P2 kg

# Step 4: Load the database dump
echo ""
echo "Step 4: Loading database from dump..."
udocker --allow-root run \
  -v "/content/dumps:/var/lib/neo4j/data/dumps" \
  kg \
  neo4j-admin database load neo4j \
    --from-path=/var/lib/neo4j/data/dumps \
    --overwrite-destination=true

# Step 5: Run the container (no --name flag here, use container name)
echo ""
echo "Step 5: Starting Neo4j container..."
echo "Neo4j will be available at:"
echo "  - Browser: http://localhost:7474"
echo "  - Bolt: bolt://localhost:7687"
echo "  - Auth: neo4j/Aq123456"
echo ""

udocker --allow-root run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/Aq123456 \
  -v "/content/dumps/neo4j.dump:/var/lib/neo4j/data/dumps/neo4j.dump" \
  kg

echo ""
echo "=========================================="
echo "Neo4j setup complete!"
echo "=========================================="