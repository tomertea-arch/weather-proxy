# Docker Compose Guide

Complete guide for running Weather Proxy with Docker Compose.

## Available Configurations

We provide 4 Docker Compose configurations for different scenarios:

| File | Use Case | Redis | Complexity |
|------|----------|-------|------------|
| `docker-compose.yml` | Default - Embedded Redis | Embedded | ⭐ Simple |
| `docker-compose.dev.yml` | Development | Embedded | ⭐ Simple |
| `docker-compose.external-redis.yml` | Testing with external Redis | External | ⭐⭐ Medium |
| `docker-compose.prod.yml` | Production | External + HA | ⭐⭐⭐ Complex |

## Quick Start

### Option 1: Embedded Redis (Simplest)

```bash
# Start with embedded Redis
docker-compose up

# Or in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: External Redis

```bash
# Start with external Redis service
docker-compose -f docker-compose.external-redis.yml up -d

# Check status
docker-compose -f docker-compose.external-redis.yml ps

# View logs
docker-compose -f docker-compose.external-redis.yml logs -f

# Stop and remove volumes
docker-compose -f docker-compose.external-redis.yml down -v
```

### Option 3: Development Mode

```bash
# Development mode with debug logging
docker-compose -f docker-compose.dev.yml up

# Access at http://localhost:8000
```

### Option 4: Production Mode

```bash
# Set Redis password
export REDIS_PASSWORD="your-secure-password"

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Check health
docker-compose -f docker-compose.prod.yml ps
```

## Detailed Usage

### 1. Default Configuration (docker-compose.yml)

**Features:**
- ✅ Embedded Redis (auto-starts)
- ✅ Single command to run
- ✅ No external dependencies
- ✅ Health checks enabled

**Usage:**
```bash
# Start
docker-compose up

# Test
curl http://localhost:8000/health
curl "http://localhost:8000/weather?city=London"

# Stop
docker-compose down
```

**When to use:**
- Quick testing
- Demos
- Local development
- CI/CD pipelines

### 2. External Redis Configuration (docker-compose.external-redis.yml)

**Features:**
- ✅ Separate Redis container
- ✅ Redis persistence enabled
- ✅ Health checks for both services
- ✅ Network isolation

**Usage:**
```bash
# Start services
docker-compose -f docker-compose.external-redis.yml up -d

# Check Redis
docker-compose -f docker-compose.external-redis.yml exec redis redis-cli ping
# Expected: PONG

# Check application
curl http://localhost:8000/health | jq .

# View logs
docker-compose -f docker-compose.external-redis.yml logs weather-proxy
docker-compose -f docker-compose.external-redis.yml logs redis

# Stop (keep data)
docker-compose -f docker-compose.external-redis.yml down

# Stop (remove data)
docker-compose -f docker-compose.external-redis.yml down -v
```

**When to use:**
- Testing with real Redis
- Integration testing
- Staging environment
- When you need Redis persistence

### 3. Development Configuration (docker-compose.dev.yml)

**Features:**
- ✅ Debug logging (LOG_LEVEL=DEBUG)
- ✅ Source code mounting (optional)
- ✅ Embedded Redis
- ✅ Quick restart

**Usage:**
```bash
# Start in development mode
docker-compose -f docker-compose.dev.yml up

# Rebuild after code changes
docker-compose -f docker-compose.dev.yml up --build

# Stop
docker-compose -f docker-compose.dev.yml down
```

**When to use:**
- Active development
- Debugging issues
- Testing code changes
- Learning the application

### 4. Production Configuration (docker-compose.prod.yml)

**Features:**
- ✅ External Redis with authentication
- ✅ Resource limits (CPU/Memory)
- ✅ High availability (2 replicas)
- ✅ Logging configuration
- ✅ Restart policies
- ✅ Optional Nginx reverse proxy

**Usage:**
```bash
# Set environment variables
export REDIS_PASSWORD="strong-password-here"

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale application
docker-compose -f docker-compose.prod.yml up -d --scale weather-proxy=3

# Check status
docker-compose -f docker-compose.prod.yml ps

# View resource usage
docker stats

# Stop gracefully
docker-compose -f docker-compose.prod.yml down
```

**With Nginx (Load Balancer):**
```bash
# Start with Nginx profile
docker-compose -f docker-compose.prod.yml --profile with-nginx up -d

# Access via Nginx
curl http://localhost/health
```

**When to use:**
- Production deployments
- Load testing
- Performance evaluation
- High availability setups

## Common Commands

### Start Services

```bash
# Foreground (see logs)
docker-compose up

# Background (detached)
docker-compose up -d

# Rebuild images
docker-compose up --build

# Force recreate
docker-compose up --force-recreate
```

### Stop Services

```bash
# Stop containers (keep data)
docker-compose down

# Stop and remove volumes (lose data)
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all
```

### View Logs

```bash
# All services
docker-compose logs

# Follow logs
docker-compose logs -f

# Specific service
docker-compose logs weather-proxy
docker-compose logs redis

# Last 50 lines
docker-compose logs --tail=50
```

### Check Status

```bash
# List services
docker-compose ps

# List all containers
docker-compose ps -a

# Top (processes)
docker-compose top
```

### Execute Commands

```bash
# Shell in application
docker-compose exec weather-proxy sh

# Check Redis
docker-compose exec redis redis-cli ping

# View application logs
docker-compose exec weather-proxy cat weather-proxy.log

# Test health endpoint
docker-compose exec weather-proxy curl http://localhost:8000/health
```

### Manage Services

```bash
# Restart service
docker-compose restart weather-proxy

# Stop service
docker-compose stop weather-proxy

# Start service
docker-compose start weather-proxy

# Remove service
docker-compose rm -f weather-proxy
```

## Environment Variables

### Application Variables

Set in `docker-compose.yml` or via `.env` file:

```bash
# .env file
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-password
LOG_LEVEL=INFO
LOG_FILE=weather-proxy.log
```

### Docker Compose Variables

```bash
# Compose project name
COMPOSE_PROJECT_NAME=weather-proxy

# File selection
COMPOSE_FILE=docker-compose.yml

# Multiple files
COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml
```

## Networking

### Access Services

```bash
# From host machine
curl http://localhost:8000/health

# From another container in same network
curl http://weather-proxy:8000/health

# Redis from host
redis-cli -h localhost -p 6379 ping
```

### Network Information

```bash
# List networks
docker network ls

# Inspect network
docker network inspect weather-proxy_weather-proxy-network

# Connect container to network
docker network connect weather-proxy_weather-proxy-network my-container
```

## Volumes

### Manage Volumes

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect weather-proxy_redis-data

# Backup volume
docker run --rm -v weather-proxy_redis-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/redis-backup.tar.gz -C /data .

# Restore volume
docker run --rm -v weather-proxy_redis-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/redis-backup.tar.gz -C /data

# Remove volume
docker volume rm weather-proxy_redis-data
```

## Health Checks

### Check Service Health

```bash
# Via Docker
docker-compose ps

# Via health endpoint
curl http://localhost:8000/health | jq .

# Check specific service
docker inspect --format='{{.State.Health.Status}}' weather-proxy
```

### Expected Health Response

```json
{
  "status": "healthy",
  "service": "weather-proxy",
  "redis": {
    "status": "connected",
    "host": "redis",
    "port": 6379
  },
  "metrics": {
    "total_requests": 10,
    "total_errors": 0
  }
}
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs weather-proxy

# Check events
docker events

# Recreate service
docker-compose up --force-recreate weather-proxy
```

### Redis Connection Issues

```bash
# Test Redis connectivity
docker-compose exec weather-proxy sh -c "redis-cli -h redis ping"

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000
# or
netstat -tuln | grep 8000

# Change port in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
```

### Out of Memory

```bash
# Check resources
docker stats

# Increase limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
```

### Rebuild Everything

```bash
# Nuclear option
docker-compose down -v --rmi all
docker-compose build --no-cache
docker-compose up
```

## Production Best Practices

### 1. Use Secrets

Don't commit passwords to git:

```yaml
# docker-compose.prod.yml
services:
  weather-proxy:
    environment:
      REDIS_PASSWORD: ${REDIS_PASSWORD}
```

```bash
# Set via environment
export REDIS_PASSWORD="secure-password"
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Resource Limits

Always set limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### 3. Logging

Configure log rotation:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 4. Health Checks

Enable health checks:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 3s
  retries: 3
```

### 5. Restart Policy

Set restart policies:

```yaml
restart: unless-stopped
# or for swarm
deploy:
  restart_policy:
    condition: on-failure
    max_attempts: 3
```

## Examples

### Example 1: Quick Test

```bash
# Start
docker-compose up -d

# Test
curl "http://localhost:8000/weather?city=London"

# Check cache
curl http://localhost:8000/metrics | grep cache

# Stop
docker-compose down
```

### Example 2: Development Workflow

```bash
# Start in dev mode
docker-compose -f docker-compose.dev.yml up

# Make code changes
# Rebuild and restart
docker-compose -f docker-compose.dev.yml up --build
```

### Example 3: Production Deployment

```bash
# Create .env file
cat > .env << EOF
REDIS_PASSWORD=super-secure-password
LOG_LEVEL=INFO
EOF

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Verify
docker-compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

### Example 4: Load Testing

```bash
# Start with external Redis
docker-compose -f docker-compose.external-redis.yml up -d

# Run load test
ab -n 1000 -c 10 http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

## Comparison Matrix

| Feature | Embedded Redis | External Redis | Production |
|---------|----------------|----------------|------------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐ Medium | ⭐⭐⭐ Complex |
| **Startup Time** | < 5s | < 10s | < 20s |
| **Data Persistence** | ❌ No | ✅ Yes | ✅ Yes |
| **Redis Monitoring** | ⚠️ Limited | ✅ Available | ✅ Full |
| **Resource Isolation** | ❌ Shared | ✅ Separate | ✅ Separate |
| **High Availability** | ❌ No | ⚠️ Single | ✅ Replicas |
| **Best For** | Dev, Test | Staging | Production |

## Next Steps

1. Choose the right configuration for your use case
2. Start with `docker-compose.yml` for testing
3. Move to `docker-compose.external-redis.yml` for staging
4. Use `docker-compose.prod.yml` for production
5. Customize as needed for your environment

## Support

- **Issues**: Check logs with `docker-compose logs`
- **Documentation**: See `README.md` and `EMBEDDED_REDIS.md`
- **Health Check**: `curl http://localhost:8000/health`

---

**Last Updated**: 2026-01-22  
**Docker Compose Version**: 3.8  
**Compatible With**: Docker 20.10+, Docker Compose 2.0+
