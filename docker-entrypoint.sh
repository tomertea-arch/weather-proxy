#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Weather Proxy - Starting...${NC}"

# Check if Redis host is provided
if [ -z "$REDIS_HOST" ] || [ "$REDIS_HOST" = "localhost" ] || [ "$REDIS_HOST" = "127.0.0.1" ]; then
    echo -e "${YELLOW}No external Redis configured. Starting embedded Redis server...${NC}"
    
    # Start Redis server in the background
    redis-server --daemonize yes \
                 --port ${REDIS_PORT:-6379} \
                 --bind 0.0.0.0 \
                 --protected-mode no \
                 --save "" \
                 --appendonly no \
                 --maxmemory 256mb \
                 --maxmemory-policy allkeys-lru
    
    # Wait for Redis to be ready
    echo "Waiting for Redis to start..."
    for i in {1..10}; do
        if redis-cli -h 127.0.0.1 -p ${REDIS_PORT:-6379} ping > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Embedded Redis server started successfully${NC}"
            break
        fi
        sleep 1
    done
    
    # Set Redis host to localhost
    export REDIS_HOST="127.0.0.1"
    export REDIS_PORT="${REDIS_PORT:-6379}"
    
    # Display Redis info
    echo "Redis Configuration:"
    echo "  Host: ${REDIS_HOST}"
    echo "  Port: ${REDIS_PORT}"
else
    echo -e "${GREEN}Using external Redis: ${REDIS_HOST}:${REDIS_PORT:-6379}${NC}"
fi

echo ""
echo -e "${GREEN}Starting Weather Proxy Application...${NC}"
echo "Listening on: http://0.0.0.0:8000"
echo ""

# Start the application
# Use exec to ensure signals are properly handled
exec uvicorn main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 10 --timeout-keep-alive 5
