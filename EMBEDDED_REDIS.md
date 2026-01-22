# Embedded Redis Server

## Overview

The Weather Proxy Docker image includes an **embedded Redis server** that automatically starts when no external Redis is configured. This makes development and testing much easier by eliminating the need for a separate Redis instance.

## How It Works

The `docker-entrypoint.sh` script intelligently detects whether to use embedded or external Redis:

### Decision Logic

```
IF REDIS_HOST is not set OR REDIS_HOST = "localhost" OR REDIS_HOST = "127.0.0.1"
  THEN: Start embedded Redis server
  ELSE: Use external Redis server
```

### Startup Sequence

1. **Check Configuration**: Script checks `REDIS_HOST` environment variable
2. **Start Redis** (if needed): Launches `redis-server` as a daemon
3. **Wait for Ready**: Verifies Redis is accepting connections
4. **Set Environment**: Updates `REDIS_HOST` to `127.0.0.1`
5. **Start Application**: Launches FastAPI with uvicorn

## Usage Examples

### Example 1: Embedded Redis (Default)

```bash
# No Redis configuration needed - embedded Redis starts automatically
docker run -p 8000:8000 weather-proxy:latest
```

**Output:**
```
Weather Proxy - Starting...
No external Redis configured. Starting embedded Redis server...
Waiting for Redis to start...
✓ Embedded Redis server started successfully
Redis Configuration:
  Host: 127.0.0.1
  Port: 6379

Starting Weather Proxy Application...
Listening on: http://0.0.0.0:8000
```

### Example 2: External Redis

```bash
# Provide REDIS_HOST - uses external Redis
docker run -p 8000:8000 \
  -e REDIS_HOST=redis.example.com \
  -e REDIS_PORT=6379 \
  weather-proxy:latest
```

**Output:**
```
Weather Proxy - Starting...
Using external Redis: redis.example.com:6379

Starting Weather Proxy Application...
Listening on: http://0.0.0.0:8000
```

### Example 3: Custom Port for Embedded Redis

```bash
# Embedded Redis on custom port
docker run -p 8000:8000 \
  -e REDIS_PORT=6380 \
  weather-proxy:latest
```

## Embedded Redis Configuration

The embedded Redis server is configured for development/testing with these settings:

| Setting | Value | Description |
|---------|-------|-------------|
| **Port** | 6379 (or `$REDIS_PORT`) | Redis listening port |
| **Bind** | 0.0.0.0 | Listen on all interfaces |
| **Daemonize** | yes | Run as background process |
| **Protected Mode** | no | Allow connections without password |
| **Persistence** | disabled | No RDB snapshots or AOF |
| **Max Memory** | 256MB | Memory limit for cache |
| **Eviction Policy** | allkeys-lru | Remove least recently used keys |

### Why These Settings?

- **No Persistence**: Data is ephemeral (container restart = fresh cache)
- **No Protected Mode**: Simplifies development (⚠️ not for production)
- **LRU Eviction**: Automatically manages memory when cache fills up
- **256MB Limit**: Reasonable size for development without consuming too much RAM

## Benefits

### ✅ Development & Testing
- **Zero Setup**: No need to install/configure Redis locally
- **Self-Contained**: Single Docker command to run everything
- **Fast Iteration**: Quick start/stop/restart cycles
- **Consistent Environment**: Same Redis version everywhere

### ✅ CI/CD Pipelines
- **Simplified Testing**: Integration tests don't need external Redis
- **Faster Builds**: No service dependencies to coordinate
- **Reliable Tests**: Isolated Redis per container

### ✅ Demos & POCs
- **Easy Demos**: Show the application without infrastructure setup
- **Quick POCs**: Test ideas without Redis deployment

## Production Considerations

### ⚠️ Not Recommended for Production

The embedded Redis is **not suitable for production** use because:

1. **No Persistence**: Data lost on container restart
2. **No Security**: No authentication configured
3. **No Monitoring**: No Redis-specific metrics
4. **Limited Resources**: Only 256MB memory
5. **No High Availability**: Single point of failure
6. **No Replication**: No data backup/redundancy

### Production Recommendations

For production, use external Redis:

#### Option 1: AWS ElastiCache
```bash
docker run -p 8000:8000 \
  -e REDIS_HOST=myredis.abc123.0001.use1.cache.amazonaws.com \
  -e REDIS_PORT=6379 \
  weather-proxy:latest
```

#### Option 2: Kubernetes with Helm Chart
```yaml
# values.yaml
redis:
  enabled: true  # Use Bitnami Redis chart
  architecture: replication
  auth:
    enabled: true
    password: "secure-password"
```

#### Option 3: External Redis Cluster
```bash
docker run -p 8000:8000 \
  -e REDIS_HOST=redis-cluster.example.com \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=your-secure-password \
  weather-proxy:latest
```

## Docker Compose Example

### Development with Embedded Redis

```yaml
version: '3.8'
services:
  weather-proxy:
    build: .
    ports:
      - "8000:8000"
    # No Redis service needed - uses embedded Redis
```

### Production with External Redis

```yaml
version: '3.8'
services:
  weather-proxy:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

volumes:
  redis-data:
```

## Troubleshooting

### Issue: "Waiting for Redis to start..." hangs

**Cause**: Redis failed to start

**Solution**: Check logs for errors
```bash
docker run -p 8000:8000 weather-proxy:latest
# Look for Redis error messages in output
```

### Issue: Application can't connect to Redis

**Cause**: Redis not accessible on expected host/port

**Solution**: Verify environment variables
```bash
docker run -p 8000:8000 \
  -e REDIS_HOST=127.0.0.1 \
  -e REDIS_PORT=6379 \
  weather-proxy:latest
```

### Issue: Redis runs out of memory

**Cause**: 256MB limit reached

**Solution**: External Redis for larger cache needs
```bash
# Use external Redis with more memory
docker run -p 8000:8000 \
  -e REDIS_HOST=your-redis-host \
  weather-proxy:latest
```

## Technical Details

### Entrypoint Script Location
`/usr/local/bin/docker-entrypoint.sh`

### Redis Server Binary
`/usr/bin/redis-server`

### Redis CLI Binary
`/usr/bin/redis-cli`

### Redis Data Directory
`/data/redis` (owned by `appuser`)

### Process Management
- **Redis**: Runs as daemon (background process)
- **Application**: Runs as PID 1 (receives signals)
- **Signal Handling**: SIGTERM properly handled for graceful shutdown

### Security Context
- **User**: `appuser` (UID 1000)
- **Redis Runs As**: `appuser` (non-root)
- **Permissions**: Redis can write to `/data/redis`

## Testing the Embedded Redis

### 1. Start Container
```bash
docker run -d --name test-weather-proxy -p 8000:8000 weather-proxy:latest
```

### 2. Check Logs
```bash
docker logs test-weather-proxy
```

Expected output:
```
Weather Proxy - Starting...
No external Redis configured. Starting embedded Redis server...
✓ Embedded Redis server started successfully
```

### 3. Test Redis Connection
```bash
# Connect to Redis CLI inside container
docker exec -it test-weather-proxy redis-cli -h 127.0.0.1

# Test commands
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> INFO server
# ... Redis info ...
127.0.0.1:6379> exit
```

### 4. Test Application
```bash
# Make requests to generate cache entries
curl "http://localhost:8000/weather?city=London"
curl "http://localhost:8000/weather?city=London"  # Should be cached

# Check cache hit in metrics
curl "http://localhost:8000/metrics" | grep cache
```

### 5. Cleanup
```bash
docker stop test-weather-proxy
docker rm test-weather-proxy
```

## Comparison: Embedded vs External Redis

| Aspect | Embedded Redis | External Redis |
|--------|----------------|----------------|
| **Setup Complexity** | ✅ Zero setup | ⚠️ Requires Redis deployment |
| **Startup Time** | ✅ < 2 seconds | ⚠️ Depends on external service |
| **Data Persistence** | ❌ No (ephemeral) | ✅ Yes (configurable) |
| **High Availability** | ❌ Single instance | ✅ Replication/clustering |
| **Resource Isolation** | ⚠️ Shares container resources | ✅ Dedicated resources |
| **Security** | ⚠️ No authentication | ✅ Configurable auth |
| **Monitoring** | ⚠️ Limited | ✅ Full metrics available |
| **Scalability** | ❌ Per-container only | ✅ Shared across replicas |
| **Best For** | Development, Testing, Demos | Production, Staging |

## Future Enhancements

Potential improvements to consider:

- [ ] Configurable memory limit via environment variable
- [ ] Optional Redis persistence in development
- [ ] Redis password support for embedded instance
- [ ] Health check includes Redis connectivity test
- [ ] Metrics export for embedded Redis
- [ ] Redis configuration file support

---

**Status**: ✅ Implemented and Working  
**Version**: 1.0.0  
**Last Updated**: 2026-01-22  
**Suitable For**: Development, Testing, CI/CD, Demos  
**Not Suitable For**: Production Deployments
