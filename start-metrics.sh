#!/bin/bash
# Quick start guide for Prometheus metrics

echo "=========================================="
echo "Smart HTTP Requester - Prometheus Setup"
echo "=========================================="
echo ""

# Check if docker is available
if command -v docker &> /dev/null; then
    echo "✓ Docker found"
    
    # Check if docker-compose is available
    if command -v docker-compose &> /dev/null; then
        echo "✓ Docker Compose found"
        echo ""
        echo "Starting Prometheus and Grafana..."
        docker-compose -f docker-compose-metrics.yml up -d
        
        echo ""
        echo "✓ Services started!"
        echo "  - Prometheus: http://localhost:9090"
        echo "  - Grafana: http://localhost:3000 (admin/admin)"
        echo ""
        echo "The application metrics endpoint: http://localhost:8000/v1/metrics"
        echo ""
        echo "To stop services, run: docker-compose -f docker-compose-metrics.yml down"
    else
        echo "✗ Docker Compose not found. Please install it."
        exit 1
    fi
else
    echo "✗ Docker not found"
    echo ""
    echo "Manual setup (without Docker):"
    echo "1. Install Prometheus from: https://prometheus.io/download/"
    echo "2. Update prometheus.yml in this directory"
    echo "3. Run: prometheus --config.file=prometheus.yml"
    echo "4. Prometheus will be available at: http://localhost:9090"
    exit 1
fi
