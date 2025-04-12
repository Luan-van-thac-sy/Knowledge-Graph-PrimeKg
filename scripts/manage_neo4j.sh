#!/bin/bash
# Script to manage Neo4j container using Docker Compose

# Change to the project root directory
cd "$(dirname "$0")/.."

# Function to display usage information
function show_usage {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start      - Start Neo4j container"
    echo "  stop       - Stop Neo4j container"
    echo "  restart    - Restart Neo4j container"
    echo "  status     - Check Neo4j container status"
    echo "  logs       - Show Neo4j container logs"
    echo "  shell      - Open a shell in the Neo4j container"
    echo "  browser    - Open Neo4j Browser in the default web browser"
    echo "  help       - Show this help message"
    echo ""
}

# Function to start Neo4j container
function start_neo4j {
    echo "Starting Neo4j container..."
    docker compose up -d neo4j
    echo "Neo4j is starting. It may take a few moments to be fully operational."
    echo "You can check the status with: $0 status"
    echo "Access Neo4j Browser at: http://localhost:7474"
    echo "Default credentials: neo4j/password"
}

# Function to stop Neo4j container
function stop_neo4j {
    echo "Stopping Neo4j container..."
    docker compose stop neo4j
}

# Function to restart Neo4j container
function restart_neo4j {
    echo "Restarting Neo4j container..."
    docker compose restart neo4j
    echo "Neo4j is restarting. It may take a few moments to be fully operational."
}

# Function to check Neo4j container status
function check_status {
    echo "Checking Neo4j container status..."
    docker compose ps neo4j
    
    # Check if Neo4j is responding
    if curl -s -I http://localhost:7474 > /dev/null; then
        echo "Neo4j Browser is accessible at: http://localhost:7474"
    else
        echo "Neo4j Browser is not yet accessible. The container might still be starting up."
    fi
}

# Function to show Neo4j container logs
function show_logs {
    echo "Showing Neo4j container logs (press Ctrl+C to exit)..."
    docker compose logs -f neo4j
}

# Function to open a shell in the Neo4j container
function open_shell {
    echo "Opening a shell in the Neo4j container..."
    docker compose exec neo4j bash
}

# Function to open Neo4j Browser in the default web browser
function open_browser {
    echo "Opening Neo4j Browser in the default web browser..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open http://localhost:7474
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        xdg-open http://localhost:7474
    else
        # Other OS
        echo "Please open http://localhost:7474 in your web browser."
    fi
}

# Process command line arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

case "$1" in
    start)
        start_neo4j
        ;;
    stop)
        stop_neo4j
        ;;
    restart)
        restart_neo4j
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs
        ;;
    shell)
        open_shell
        ;;
    browser)
        open_browser
        ;;
    help)
        show_usage
        ;;
    *)
        echo "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

exit 0
