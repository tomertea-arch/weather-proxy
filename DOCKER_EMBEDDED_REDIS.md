# Quick Reference: Embedded Redis in Docker

## TL;DR

The Docker image now includes Redis server and automatically starts it if you don't provide an external Redis host.

```bash
# Just run it - Redis starts automatically!
docker run -p 8000:8000 weather-proxy:latest
```

## Usage Patterns

### Development (Embedded Redis)
```bash
docker run -p 8000:8000 weather-proxy:latest
```

### Production (External Redis)
```bash
docker run -p 8000:8000 \
  -e REDIS_HOST=redis.production.com \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=secure-password \
  weather-proxy:latest
```

### Testing (Embedded Redis)
```bash
docker run --rm -p 8000:8000 weather-proxy:latest
```

## Environment Variables

| Variable | Default | Effect |
|----------|---------|--------|
| `REDIS_HOST` | Not set | **Not set**: Embedded Redis starts<br>**Set**: Uses external Redis |
| `REDIS_PORT` | 6379 | Port for Redis (embedded or external) |
| `REDIS_PASSWORD` | Not set | Password for external Redis |

## How It Decides

```
if REDIS_HOST is empty or "localhost" or "127.0.0.1":
    Start embedded Redis
    Use localhost:6379
else:
    Use external Redis at REDIS_HOST:REDIS_PORT
```

## What You Get

### With Embedded Redis
- ✅ Zero configuration
- ✅ Fast startup (~2 seconds)
- ✅ 256MB cache memory
- ✅ LRU eviction policy
- ⚠️ No data persistence
- ⚠️ No authentication

### With External Redis
- ✅ Data persistence
- ✅ High availability options
- ✅ Authentication support
- ✅ Unlimited memory (based on server)
- ✅ Shared cache across containers
- ⚠️ Requires Redis server

## Complete Example

### 1. Build Image
```bash
docker build -t weather-proxy:latest .
```

### 2. Run with Embedded Redis
```bash
docker run -d --name wp -p 8000:8000 weather-proxy:latest
```

### 3. Test It
```bash
# Check logs to see Redis started
docker logs wp

# Test the API
curl "http://localhost:8000/weather?city=London"

# Check Redis is working (inside container)
docker exec -it wp redis-cli -h 127.0.0.1 PING
# Response: PONG

# Check cache metrics
curl http://localhost:8000/metrics | grep cache
```

### 4. Cleanup
```bash
docker stop wp && docker rm wp
```

## Docker Compose

### Embedded Redis (Simple)
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
```

### External Redis (Production)
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
    depends_on:
      - redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
volumes:
  redis-data:
```

## Kubernetes/Helm

The Helm chart already supports both modes:

### Embedded Redis (Dev)
```yaml
redis:
  enabled: false  # Don't deploy Redis chart
  
# REDIS_HOST not set = embedded Redis starts
```

### External Redis (Prod)
```yaml
redis:
  enabled: true  # Deploy Redis via Bitnami chart
  
config:
  redis:
    host: weather-proxy-redis-master
```

## File Changes Made

1. **Dockerfile**:
   - Added `redis-server` and `redis-tools`
   - Created `/data/redis` directory
   - Copied `docker-entrypoint.sh`
   - Changed CMD to ENTRYPOINT

2. **docker-entrypoint.sh** (New):
   - Detects Redis configuration
   - Starts Redis if needed
   - Starts FastAPI application

3. **README.md**:
   - Updated with embedded Redis documentation
   - Added usage examples

4. **EMBEDDED_REDIS.md** (New):
   - Comprehensive documentation
   - Configuration details
   - Troubleshooting guide

## Common Issues

**Q: Redis fails to start**  
A: Check logs with `docker logs <container>`. Ensure port 6379 is not in use.

**Q: Want to disable embedded Redis?**  
A: Set `REDIS_HOST` to any external host or `none`.

**Q: How much memory does Redis use?**  
A: Limited to 256MB with LRU eviction.

**Q: Is data persisted?**  
A: No, embedded Redis is ephemeral (for development).

**Q: Can I use this in production?**  
A: Not recommended. Use external Redis with persistence and HA.

---

For full documentation, see [EMBEDDED_REDIS.md](EMBEDDED_REDIS.md)
