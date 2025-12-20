#!/bin/bash

echo "========================================"
echo "PostgreSQL Database Reinitialization"
echo "========================================"
echo ""
echo "This script will:"
echo "1. Stop all containers"
echo "2. Remove PostgreSQL data directory"
echo "3. Restart containers with NEW credentials"
echo ""
echo "⚠️  WARNING: This will DELETE all existing data in PostgreSQL!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Stopping containers..."
docker compose -f docker-compose.min.yaml down

echo ""
echo "Step 2: Removing PostgreSQL data directory..."
if [ -d "./tmp/postgres" ]; then
    sudo rm -rf ./tmp/postgres
    echo "  ✓ Removed ./tmp/postgres"
else
    echo "  ℹ Directory ./tmp/postgres does not exist (skipping)"
fi

if [ -d "./tmp/beagle-redis" ]; then
    read -p "Also remove Redis data? (yes/no): " redis_confirm
    if [ "$redis_confirm" = "yes" ]; then
        sudo rm -rf ./tmp/beagle-redis
        echo "  ✓ Removed ./tmp/beagle-redis"
    fi
fi

echo ""
echo "Step 3: Starting containers with NEW credentials from .env..."
docker compose -f docker-compose.min.yaml up -d

echo ""
echo "Step 4: Waiting for PostgreSQL to initialize (30 seconds)..."
sleep 30

echo ""
echo "Step 5: Verifying PostgreSQL connection..."
docker exec beagle-postgres pg_isready -U beagle -d beagle_db

echo ""
echo "Step 6: Testing database access..."
docker exec beagle-postgres psql -U beagle -d beagle_db -c "SELECT version();"

echo ""
echo "========================================"
echo "✓ Reinitialization complete!"
echo ""
echo "pgAdmin Connection Settings:"
echo "  Host: localhost"
echo "  Port: 5434"
echo "  Database: beagle_db"
echo "  Username: beagle"
echo "  Password: beagle_password"
echo "========================================"
