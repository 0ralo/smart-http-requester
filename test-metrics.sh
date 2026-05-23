#!/bin/bash
# Examples of testing the application with metrics collection

echo "=========================================="
echo "Smart HTTP Requester - Testing Examples"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"
METRICS_URL="$BASE_URL/v1/metrics"

echo "Base URL: $BASE_URL"
echo "Metrics URL: $METRICS_URL"
echo ""

# Test 1: Check if server is running
echo -e "${YELLOW}Test 1: Check server status${NC}"
if curl -s "$BASE_URL/docs" > /dev/null; then
    echo -e "${GREEN}✓ Server is running${NC}"
else
    echo -e "${RED}✗ Server is not running${NC}"
    echo "Please start the server with: python -m uvicorn application:app"
    exit 1
fi
echo ""

# Test 2: Register a user
echo -e "${YELLOW}Test 2: Register a user${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password_hash":"5d41402abc4b2a76b9719d911017c592"}')
echo "Response: $REGISTER_RESPONSE"
echo ""

# Extract token from register response (adjust as needed based on your API response)
# For now, we'll use a placeholder

# Test 3: Login
echo -e "${YELLOW}Test 3: Login${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password_hash":"5d41402abc4b2a76b9719d911017c592"}')
echo "Response: $LOGIN_RESPONSE"
echo ""

# Extract token (this is a simplified example)
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${YELLOW}Note: Could not extract token. Using dummy token for examples.${NC}"
    TOKEN="dummy_token_for_examples"
fi

echo ""

# Test 4: Create a task
echo -e "${YELLOW}Test 4: Create a task${NC}"
TASK_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/requests" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "url": "https://example.com",
    "method": "GET",
    "headers": {},
    "body": null,
    "max_attempts": 3
  }')
echo "Response: $TASK_RESPONSE"
echo ""

# Test 5: Get tasks
echo -e "${YELLOW}Test 5: Get user tasks${NC}"
curl -s -X GET "$BASE_URL/v1/requests?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN" | head -c 200
echo "..."
echo ""

# Test 6: Check metrics
echo -e "${YELLOW}Test 6: View metrics${NC}"
echo "Fetching metrics from: $METRICS_URL"
echo ""
METRICS=$(curl -s "$METRICS_URL")
echo "Metrics (first 500 chars):"
echo "$METRICS" | head -c 500
echo ""
echo ""

# Test 7: Filter specific metrics
echo -e "${YELLOW}Test 7: Filter specific metrics${NC}"
echo "HTTP Requests Total:"
echo "$METRICS" | grep -E "^http_requests_total\{" | head -5
echo ""
echo "Auth Attempts:"
echo "$METRICS" | grep -E "^auth_attempts_total\{" | head -5
echo ""
echo "Tasks Created:"
echo "$METRICS" | grep -E "^tasks_created_total"
echo ""

echo -e "${GREEN}=========================================="
echo "Testing complete!"
echo "==========================================${NC}"
echo ""
echo "View full metrics at: $METRICS_URL"
echo "View Prometheus UI at: http://localhost:9090 (if running)"
echo "View Grafana at: http://localhost:3000 (if running)"
