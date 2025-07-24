#!/bin/bash

# NeuroSync Synapse Setup Script
# Usage: ./setup_synapse.sh <SYNAPSE_SERVER_NAME> <ADMIN_PASSWORD> <NS_ADMIN_TOKEN>

set -e  # Exit on any error

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <SYNAPSE_SERVER_NAME> <ADMIN_PASSWORD> <NS_ADMIN_TOKEN>"
    echo "Example: $0 matrix.example.com my_password admin_token"
    exit 1
fi

SYNAPSE_SERVER_NAME="$1"
ADMIN_PASSWORD="$2"
NS_ADMIN_TOKEN="$3"

echo "NeuroSync Synapse Setup"
echo "Server Name: $SYNAPSE_SERVER_NAME"
echo "Admin Password: $ADMIN_PASSWORD"
echo "Admin Token: $NS_ADMIN_TOKEN"
echo ""

# Add synapse service to docker-compose.yml
cat >> docker-compose.yml << EOF

  synapse:
    container_name: synapse
    image: matrixdotorg/synapse:latest
    restart: always
    ports:
      - 8008:8008
    volumes:
      - ../synapse/data:/data
    networks:
      - matrix-net
EOF

echo "Synapse service added to docker-compose.yml"

# Create .env file with required variables
cat > .env << EOF
MATRIX_HOMESERVER=http://synapse:8008
NS_ADMIN_TOKEN=$NS_ADMIN_TOKEN
EOF

echo ".env file created with Matrix configuration"

# Create synapse directory
cd ..
mkdir -p synapse/
echo "Synapse directory created"

# Create data directory inside synapse
cd synapse/
mkdir -p data/
echo "Data directory created"

# Generate synapse configuration
echo "Generating Synapse configuration..."
docker run -it --rm \
    -v ./data:/data \
    -e SYNAPSE_SERVER_NAME="$SYNAPSE_SERVER_NAME" \
    -e SYNAPSE_REPORT_STATS=yes \
    matrixdotorg/synapse:latest generate

echo "Synapse configuration generated"

# Change ownership of data directory
sudo chown -R 991:991 data/
echo "Data directory ownership updated"

# Go back to NeuroSync directory
cd ../NeuroSync/

# Create matrix-net network if it doesn't exist
if ! docker network inspect matrix-net >/dev/null 2>&1; then
    echo "Creating matrix-net network..."
    docker network create matrix-net
fi

# Start services in detached mode
echo "Starting services in detached mode..."
docker compose up -d

echo "Waiting for Synapse..."
sleep 10

# Register admin user
echo "Registering admin user..."
docker exec -it synapse register_new_matrix_user \
    -u admin \
    -p "$ADMIN_PASSWORD" \
    -a \
    -c /data/homeserver.yaml \
    http://localhost:8008

echo ""
echo "Setup completed successfully!"
echo ""
echo "  - Synapse server: $SYNAPSE_SERVER_NAME"
echo "  - Synapse URL: http://localhost:8008"
echo "  - Admin user: admin"
echo "  - Admin password: $ADMIN_PASSWORD"
echo "  - NeuroSync admin token: $NS_ADMIN_TOKEN"
echo ""
echo "Services are running in detached mode."
echo "   Use 'docker compose logs' to view logs"
echo "   Use 'docker compose down' to stop services"
