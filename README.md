# Weather Proxy Microservice

A production-ready FastAPI-based proxy microservice with Redis caching, optimized for containerized deployments (Docker, Kubernetes, AWS Fargate).

**Author**: Tomer Traivish (trivish@hotmail.com)  
**Repository**: https://github.com/tomertea-arch/weather-proxy

## Table of Contents

- [Features](#features)
- [Local Setup and Run Instructions](#local-setup-and-run-instructions)
- [Architectural Design Decisions](#architectural-design-decisions)
- [API Endpoints](#api-endpoints)
- [Docker Deployment](#docker-deployment)
- [Kubernetes/Helm Deployment](#kuberneteshelm-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Testing](#testing)
- [Monitoring & Observability](#monitoring--observability)
- [Future Improvements](#future-improvements)
- [Documentation](#documentation)

## Features

### Core Functionality
- ✅ **FastAPI Framework** - High-performance async API with automatic OpenAPI docs
- ✅ **Redis Caching** - Response caching with configurable TTL (10 minutes for weather)
- ✅ **Weather API Integration** - Open-Meteo API for weather data with geocoding
- ✅ **Prometheus Metrics** - `/metrics` endpoint in Prometheus format

### Reliability & Resilience
- ✅ **Retry Mechanism** - Exponential backoff with up to 3 attempts for weather API
- ✅ **Circuit Breaker Pattern** - Prevents cascading failures
- ✅ **Graceful Shutdown** - SIGTERM/SIGINT signal handling with 30s grace period
- ✅ **Health Checks** - `/health` endpoint with detailed metrics and Redis status

### Operations & Monitoring
- ✅ **Structured Logging** - File and console logging with rotation
- ✅ **Request Metrics** - Duration, count, errors, cache hit/miss tracking
- ✅ **Upstream Tracking** - Status codes from external services
- ✅ **Embedded Redis** - Auto-starts if no external Redis configured

### Security & Best Practices
- ✅ **Non-root User** - Runs as user 1000 in Docker
- ✅ **Security Contexts** - Proper Kubernetes security configurations
- ✅ **Input Validation** - Pydantic models for request validation
- ✅ **Safe Deserialization** - JSON instead of eval() for cache

### Deployment Options
- ✅ **Docker** - Multi-stage optimized Dockerfile with embedded Redis
- ✅ **Docker Compose** - 4 configurations (dev, staging, prod)
- ✅ **Kubernetes/Helm** - Production-ready Helm chart
- ✅ **AWS Fargate** - Optimized for serverless containers

---

## Local Setup and Run Instructions

### Prerequisites

- **Python 3.10+** (Python 3.11 recommended)
- **Git**
- **Docker** (optional, for containerized deployment)
- **Docker Compose** (optional, for multi-service setup)

### Option 1: Python Virtual Environment (Development)

#### 1. Clone the Repository

```bash
git clone https://github.com/tomertea-arch/weather-proxy.git
cd weather-proxy
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On Linux/Mac:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Run the Application

```bash
# Without Redis (will fail gracefully but still work for non-cached requests)
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# With auto-reload for development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Weather endpoint
curl "http://localhost:8000/weather?city=London"

# Metrics
curl http://localhost:8000/metrics
```

### Option 2: Docker (Recommended)

#### 1. Build Docker Image

```bash
docker build -t weather-proxy:latest .
```

#### 2. Run with Embedded Redis (Simplest)

```bash
# The container includes Redis and starts it automatically
docker run -p 8000:8000 weather-proxy:latest
```

**Output:**
```
Weather Proxy - Starting...
No external Redis configured. Starting embedded Redis server...
✓ Embedded Redis server started successfully
Redis Configuration:
  Host: 127.0.0.1
  Port: 6379

Starting Weather Proxy Application...
Listening on: http://0.0.0.0:8000
```

#### 3. Test the API

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/weather?city=Paris"
curl http://localhost:8000/metrics | grep cache
```

### Option 3: Docker Compose (Full Stack)

#### 1. Default Configuration (Embedded Redis)

```bash
# Start services
docker-compose up

# Or in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

#### 2. With External Redis

```bash
# Start with separate Redis container
docker-compose -f docker-compose.external-redis.yml up -d

# Check status
docker-compose -f docker-compose.external-redis.yml ps

# View logs
docker-compose -f docker-compose.external-redis.yml logs -f
```

#### 3. Development Mode

```bash
# Start in development mode (debug logging)
docker-compose -f docker-compose.dev.yml up
```

#### 4. Production Mode

```bash
# Set Redis password
export REDIS_PASSWORD="your-secure-password"

# Start production stack
docker-compose -f docker-compose.prod.yml up -d

# Scale application
docker-compose -f docker-compose.prod.yml up -d --scale weather-proxy=3
```

### Testing the Installation

After starting the application, verify it's working:

```bash
# 1. Check health
curl http://localhost:8000/health | jq .

# Expected response:
# {
#   "status": "healthy",
#   "service": "weather-proxy",
#   "redis": {...},
#   "metrics": {...}
# }

# 2. Test weather endpoint
curl "http://localhost:8000/weather?city=London" | jq .

# 3. Test caching (second request should be faster)
time curl "http://localhost:8000/weather?city=London"

# 4. Check metrics
curl http://localhost:8000/metrics | grep weather_proxy_requests_total

# 5. View OpenAPI documentation
# Open browser: http://localhost:8000/docs
```

### Environment Configuration

Create a `.env` file for custom configuration:

```bash
# Copy example
cp env.example .env

# Edit configuration
nano .env
```

**Available Variables:**
```bash
# Redis
REDIS_HOST=localhost          # Empty for embedded Redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=               # Optional

# Logging
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
LOG_FILE=weather-proxy.log
```

---

## Architectural Design Decisions

### 1. Technology Stack

#### FastAPI Framework
**Decision**: Use FastAPI instead of Flask or Django

**Rationale:**
- ✅ **Async Support**: Native async/await for non-blocking I/O operations
- ✅ **Performance**: One of the fastest Python frameworks (comparable to Node.js)
- ✅ **Type Safety**: Pydantic integration for automatic validation and serialization
- ✅ **Auto Documentation**: Automatic OpenAPI (Swagger) and ReDoc documentation
- ✅ **Modern Python**: Leverages Python 3.10+ type hints

**Trade-offs:**
- ❌ Smaller ecosystem than Flask
- ❌ Team learning curve for async patterns

#### Redis for Caching
**Decision**: Use Redis as the caching layer

**Rationale:**
- ✅ **Speed**: In-memory storage with microsecond latency
- ✅ **Persistence Options**: RDB and AOF for data durability
- ✅ **Mature**: Battle-tested in production environments
- ✅ **Simple**: Key-value store is perfect for API response caching
- ✅ **TTL Support**: Built-in expiration for cache entries

**Trade-offs:**
- ❌ Additional service to manage
- ❌ Memory constraints (mitigated with LRU eviction)

**Alternative Considered**: In-memory Python dict (rejected due to lack of TTL and persistence)

#### Embedded Redis in Docker
**Decision**: Include Redis server in the Docker image

**Rationale:**
- ✅ **Developer Experience**: Zero configuration needed for local development
- ✅ **CI/CD Simplification**: Tests don't need external services
- ✅ **Quick Demos**: Single container runs everything
- ✅ **Flexibility**: Still supports external Redis for production

**Trade-offs:**
- ❌ Larger Docker image (added ~50MB)
- ❌ Not suitable for production (by design)

**Implementation**: Smart entrypoint script detects if external Redis is configured and only starts embedded Redis when needed.

### 2. Caching Strategy

#### Cache Key Design
**Decision**: Use `cache_key = f"{endpoint}:{param1}:{param2}"`

**Example**: `weather:London` or `proxy:https://api.example.com:/data`

**Rationale:**
- ✅ **Predictable**: Easy to debug and invalidate
- ✅ **Collision-free**: Unique keys per resource
- ✅ **Readable**: Human-readable cache keys

#### TTL Strategy
**Decision**: 600 seconds (10 minutes) for weather data

**Rationale:**
- ✅ **Balance**: Fresh enough for weather (changes gradually)
- ✅ **Performance**: Significantly reduces API calls
- ✅ **Cost**: Reduces external API costs

**Configurable**: Could be made environment-variable driven

#### Cache-Aside Pattern
**Decision**: Application manages cache (not cache-through)

**Flow**:
1. Check cache for key
2. If hit → return cached data
3. If miss → fetch from API
4. Store in cache
5. Return data

**Rationale:**
- ✅ **Control**: Application has full control over cache logic
- ✅ **Resilience**: Works even if Redis is down
- ✅ **Selective**: Can choose what to cache

### 3. Retry Mechanism

#### Exponential Backoff
**Decision**: Use Tenacity library with exponential backoff

**Configuration**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
)
```

**Rationale:**
- ✅ **Resilience**: Handles transient failures (network glitches, rate limits)
- ✅ **Exponential**: Reduces load on failing services (1s, 2s, 4s delays)
- ✅ **Bounded**: Maximum 3 attempts prevents infinite loops
- ✅ **Selective**: Only retries on specific error types

**Trade-offs:**
- ❌ Increased latency on failures (acceptable for weather data)
- ❌ More complex error handling

### 4. Graceful Shutdown

#### Signal Handling
**Decision**: Implement lifespan context manager with signal handlers

**Implementation**:
- Registers SIGTERM and SIGINT handlers
- 2-second grace period for in-flight requests
- Closes HTTP and Redis connections
- 10-second uvicorn graceful shutdown timeout

**Rationale:**
- ✅ **Zero-Downtime**: Completes active requests before shutdown
- ✅ **Resource Cleanup**: Prevents connection leaks
- ✅ **Fargate Compatible**: Finishes within 30-second timeout
- ✅ **Kubernetes Native**: Works with rolling updates

**Critical for**:
- AWS Fargate task termination
- Kubernetes pod lifecycle
- Docker container stops

### 5. Monitoring & Observability

#### Prometheus Metrics
**Decision**: Expose `/metrics` endpoint in Prometheus format

**Metrics Tracked**:
- Request count (by endpoint, method, status)
- Request duration (histogram with buckets)
- Error count (by type)
- Cache operations (hit/miss/error)
- Redis connection status
- Upstream status codes

**Rationale:**
- ✅ **Standard Format**: Works with any Prometheus-compatible system
- ✅ **Rich Metrics**: Covers all important dimensions
- ✅ **Query Friendly**: Easy to create dashboards and alerts
- ✅ **Low Overhead**: In-memory aggregation

**Tools Supported**:
- Prometheus + Grafana
- AWS CloudWatch
- Datadog, New Relic, etc.

#### Structured Logging
**Decision**: Python logging with RotatingFileHandler

**Format**: `[TIMESTAMP] LEVEL - MESSAGE`

**Rationale:**
- ✅ **File + Console**: Can capture logs in both places
- ✅ **Rotation**: Prevents disk fill-up (10MB x 3 files)
- ✅ **Structured**: Consistent format for parsing
- ✅ **Levels**: DEBUG, INFO, WARNING, ERROR for filtering

**Future Enhancement**: Could migrate to JSON logging for better parsing

### 6. API Design

#### RESTful Endpoints
**Decision**: Use REST principles with clear resource naming

**Endpoints**:
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /weather?city={name}` - Weather data

**Rationale:**
- ✅ **Familiar**: REST is widely understood
- ✅ **HTTP Semantics**: Uses appropriate HTTP methods
- ✅ **Queryable**: Query parameters for filtering/options
- ✅ **Versioned**: Ready for `/v1/` prefix if needed

#### Error Handling
**Decision**: Use FastAPI HTTPException with appropriate status codes

**Status Codes**:
- `200 OK` - Success
- `400 Bad Request` - Missing parameters
- `404 Not Found` - City not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Application error
- `502 Bad Gateway` - Upstream service error
- `503 Service Unavailable` - Redis unavailable

**Rationale:**
- ✅ **Standard HTTP**: Clients can handle errors properly
- ✅ **Detailed**: Error messages explain what went wrong
- ✅ **Consistent**: Same error format across all endpoints

### 7. Security

#### Non-Root User
**Decision**: Run application as user 1000 in Docker

**Rationale:**
- ✅ **Principle of Least Privilege**: Limits blast radius of vulnerabilities
- ✅ **Best Practice**: Recommended by Docker and Kubernetes
- ✅ **Compliance**: Required by many security policies

#### Input Validation
**Decision**: Use Pydantic models for all inputs

**Rationale:**
- ✅ **Type Safety**: Automatic validation and type coercion
- ✅ **Injection Prevention**: Prevents injection attacks
- ✅ **Documentation**: Auto-generates OpenAPI schemas

#### Safe Deserialization
**Decision**: Use `json.loads()` instead of `eval()` for cache

**Rationale:**
- ✅ **Security**: Prevents arbitrary code execution
- ✅ **Standard**: JSON is the web standard
- ✅ **Type Safety**: Works with Pydantic models

### 8. Testing Strategy

#### Layered Testing
**Decision**: Unit tests + Integration tests

**Structure**:
- **Unit Tests** (test_main.py): Test individual components
- **Integration Tests** (test_integration.py): Test component interactions

**Coverage**:
- 28 unit tests (26 passing - 92.9%)
- 19 integration tests (19 passing - 100%)
- 47 total tests

**Rationale:**
- ✅ **Fast Feedback**: Unit tests run in seconds
- ✅ **Comprehensive**: Integration tests validate real interactions
- ✅ **Confidence**: High test coverage for refactoring

**Mocking Strategy**:
- Mock Redis for isolation
- Mock HTTP client for external APIs
- Reset metrics between tests

### 9. Deployment Architecture

#### Multi-Environment Support
**Decision**: Provide configurations for dev, staging, prod

**Artifacts**:
- Docker Compose (4 configurations)
- Helm Chart (with values-production.yaml, values-staging.yaml)
- Environment-specific settings

**Rationale:**
- ✅ **Flexibility**: Same codebase, different configs
- ✅ **Safety**: Production has stricter settings
- ✅ **Developer Experience**: Easy local development

#### Kubernetes-Ready
**Decision**: Full Helm chart with all production features

**Includes**:
- Deployment with HPA
- Service and Ingress
- ConfigMap and Secrets
- PodDisruptionBudget
- ServiceMonitor (Prometheus)

**Rationale:**
- ✅ **Production-Ready**: All necessary components
- ✅ **Scalable**: Auto-scaling configured
- ✅ **Reliable**: High availability settings
- ✅ **Observable**: Monitoring integration

---

## API Endpoints

### Core Endpoints

#### `GET /` - Root
Basic service information.

**Response**:
```json
{
  "service": "Weather Proxy Service",
  "version": "1.0.0",
  "status": "running"
}
```

#### `GET /health` - Health Check
Health check with detailed metrics and Redis status.

**Response**:
```json
{
  "status": "healthy",
  "service": "weather-proxy",
  "redis": {
    "status": "connected",
    "host": "127.0.0.1",
    "port": 6379
  },
  "metrics": {
    "total_requests": 150,
    "total_errors": 2,
    "requests_by_endpoint": {
      "/weather": 80,
      "/proxy/GET": 50,
      "/health": 20
    },
    "request_duration": {
      "count": 150,
      "avg_ms": 45.2,
      "min_ms": 5.1,
      "max_ms": 320.5
    },
    "upstream_status_codes": {
      "200": 148,
      "500": 2
    }
  }
}
```

#### `GET /weather?city={city_name}` - Weather Data
Get weather data for a city (cached for 10 minutes).

**Parameters**:
- `city` (required): City name (e.g., "London", "Paris", "Tokyo")

**Response**:
```json
{
  "city": "London",
  "coordinates": {
    "latitude": 51.5074,
    "longitude": -0.1278
  },
  "weather": {
    "temperature": 15.5,
    "windspeed": 12.0,
    "winddirection": 240,
    "weathercode": 3,
    "time": "2026-01-22T12:00"
  },
  "cached": false,
  "timestamp": "2026-01-22T12:00:05"
}
```

**Features**:
- Geocoding: Converts city name to coordinates
- Retry mechanism: Up to 3 attempts with exponential backoff
- Caching: 10-minute TTL
- Error handling: 404 if city not found

#### `GET /metrics` - Prometheus Metrics
Metrics in Prometheus format for monitoring.

**Format**: Prometheus text format

**Sample**:
```
# HELP weather_proxy_requests_total Total number of requests
# TYPE weather_proxy_requests_total counter
weather_proxy_requests_total{endpoint="/weather",method="GET",status="200"} 150

# HELP weather_proxy_request_duration_seconds Request duration
# TYPE weather_proxy_request_duration_seconds histogram
weather_proxy_request_duration_seconds_bucket{le="0.05"} 45
weather_proxy_request_duration_seconds_count 150
weather_proxy_request_duration_seconds_sum 6.78

# HELP weather_proxy_cache_operations_total Cache operations
# TYPE weather_proxy_cache_operations_total counter
weather_proxy_cache_operations_total{operation="get",result="hit"} 75
weather_proxy_cache_operations_total{operation="get",result="miss"} 75
```

---

## Docker Deployment

### Building the Image

```bash
docker build -t weather-proxy:latest .
```

### Running the Container

#### With Embedded Redis
```bash
docker run -p 8000:8000 weather-proxy:latest
```

#### With External Redis
```bash
docker run -p 8000:8000 \
  -e REDIS_HOST=redis.example.com \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD=secret \
  weather-proxy:latest
```

### Docker Compose

See [DOCKER_COMPOSE_GUIDE.md](DOCKER_COMPOSE_GUIDE.md) for detailed documentation.

**Quick Start**:
```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up -d
```

---

## Kubernetes/Helm Deployment

### Quick Install

```bash
helm install weather-proxy ./helm/weather-proxy \
  --set image.repository=your-registry/weather-proxy \
  --set image.tag=1.0.0
```

### Production Install

```bash
helm install weather-proxy ./helm/weather-proxy \
  -f ./helm/weather-proxy/values-production.yaml \
  --namespace weather-proxy-prod \
  --create-namespace
```

See [helm/HELM_DEPLOYMENT.md](helm/HELM_DEPLOYMENT.md) for comprehensive documentation.

---

## CI/CD Pipeline

This project includes a comprehensive GitHub Actions CI/CD pipeline that automatically:

- ✅ **Runs code linters** (flake8, black, pylint)
- ✅ **Executes the full test suite** (unit + integration tests)
- ✅ **Builds Docker images** with multi-architecture support
- ✅ **Scans for security vulnerabilities** using Trivy
- ✅ **Pushes to Docker registries** (Docker Hub + GitHub Container Registry)

### Pipeline Stages

```
lint → test → docker-build → [docker-push, security-scan]
```

### Quick Start

The pipeline runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Configuration

**Required GitHub Secrets** (for Docker push):
- `DOCKERHUB_USERNAME` - Your Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub access token

### Local CI Simulation

```bash
# Run linting
pip install flake8 black pylint
flake8 . --exclude=venv,.venv,__pycache__
black --check .

# Run tests with coverage
pytest -v --cov=main --cov-report=html

# Build and test Docker image
docker build -t weather-proxy:test .
docker run -d --name test -p 8000:8000 weather-proxy:test
curl http://localhost:8000/health
docker stop test && docker rm test

# Scan for vulnerabilities
trivy image weather-proxy:test
```

### Documentation

For comprehensive CI/CD documentation, see [CI_CD.md](CI_CD.md).

---

## Testing

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=main --cov-report=html

# Run specific test file
pytest test_main.py -v
pytest test_integration.py -v

# Run specific test
pytest test_main.py::TestWeatherEndpoint::test_weather_missing_city_parameter -v
```

### Test Coverage

- **Unit Tests**: 28 tests (test_main.py) - 92.9% passing
- **Integration Tests**: 19 tests (test_integration.py) - 100% passing
- **Total**: 47 tests - 95.7% passing

See [INTEGRATION_TESTS.md](INTEGRATION_TESTS.md) for detailed documentation.

---

## Monitoring & Observability

### Metrics Collection

The `/metrics` endpoint exposes Prometheus-compatible metrics:

```bash
# Scrape metrics
curl http://localhost:8000/metrics

# Integration with Prometheus
# Add to prometheus.yml:
scrape_configs:
  - job_name: 'weather-proxy'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

### Logging

Logs are written to:
- **Console**: stdout (for containers)
- **File**: `weather-proxy.log` (rotating, 10MB x 3 files)

```bash
# View logs in Docker
docker logs -f weather-proxy

# View logs in Kubernetes
kubectl logs -f deployment/weather-proxy
```

### Grafana Dashboards

Import metrics into Grafana for visualization:
- Request rate
- Error rate
- Latency percentiles (p50, p95, p99)
- Cache hit ratio
- Upstream status codes

---

## Future Improvements

### High Priority (Would implement given more time)

#### 1. Authentication & Authorization
**Current State**: No authentication

**Improvements**:
- Add API key authentication
- JWT token support
- Rate limiting per user/API key
- OAuth2 integration for enterprise SSO

**Benefits**:
- Prevent abuse
- Track usage per client
- Monetization options
- Enterprise-ready

**Implementation**:
```python
# FastAPI dependency
from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/weather")
async def weather(city: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Validate API key
    pass
```

#### 2. Rate Limiting
**Current State**: No rate limiting

**Improvements**:
- Per-client rate limits (e.g., 100 req/min)
- Sliding window algorithm
- Redis-backed rate limiting
- Different tiers (free, premium)

**Benefits**:
- Prevent DDoS
- Fair resource usage
- Cost control

**Libraries**: `slowapi`, `fastapi-limiter`

#### 3. Request/Response Schema Validation
**Current State**: Basic validation

**Improvements**:
- Stricter input validation
- Output schema validation
- API versioning (`/v1/`, `/v2/`)
- Backward compatibility

**Benefits**:
- API stability
- Better error messages
- Documentation accuracy

#### 4. Advanced Caching Strategies
**Current State**: Simple TTL-based caching

**Improvements**:
- **Conditional Caching**: Based on request parameters
- **Cache Warming**: Preload popular data
- **Cache Invalidation API**: Manual cache clear
- **Cache Tiering**: L1 (memory) + L2 (Redis)
- **Smart TTL**: Vary by endpoint or data freshness

**Example**:
```python
# Short TTL for rapidly changing data
cache_ttl = {
    "weather": 600,      # 10 minutes
    "forecast": 3600,    # 1 hour
    "historical": 86400  # 24 hours
}
```

#### 5. Distributed Tracing
**Current State**: Basic logging

**Improvements**:
- OpenTelemetry integration
- Distributed trace IDs
- Span creation for external calls
- Integration with Jaeger/Zipkin

**Benefits**:
- Debug cross-service calls
- Visualize request flow
- Identify bottlenecks

**Implementation**:
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(app)
```

#### 6. Database for Persistent Storage
**Current State**: Cache-only (ephemeral)

**Improvements**:
- PostgreSQL for request logs
- Analytics database (time-series)
- Store API usage statistics
- Historical weather data

**Benefits**:
- Long-term analytics
- Audit trails
- Business intelligence

### Medium Priority

#### 7. Advanced Error Handling
**Improvements**:
- Structured error responses
- Error codes (APP-001, APP-002)
- Client retry hints
- Detailed error documentation

**Example**:
```json
{
  "error": {
    "code": "WEATHER_API_UNAVAILABLE",
    "message": "Weather service is temporarily unavailable",
    "retry_after": 60,
    "details": {...}
  }
}
```

#### 8. Configuration Management
**Current State**: Environment variables

**Improvements**:
- Configuration service (Consul, etcd)
- Dynamic config reload
- Feature flags
- A/B testing support

**Benefits**:
- Change config without restart
- Gradual rollouts
- Environment-specific features

#### 9. Webhooks & Callbacks
**Improvements**:
- Subscribe to weather updates
- Webhook delivery
- Event-driven architecture
- Async notifications

**Use Case**:
```python
@app.post("/subscriptions")
async def subscribe(city: str, webhook_url: str):
    # Notify webhook when weather changes
    pass
```

#### 10. GraphQL API
**Current State**: REST only

**Improvements**:
- GraphQL endpoint
- Query exactly what you need
- Reduce over-fetching
- Better for mobile clients

**Benefits**:
- Flexible queries
- Fewer API calls
- Typed schema

#### 11. Multi-Region Support
**Improvements**:
- Deploy to multiple regions
- Geo-routing
- Regional caches
- Data locality

**Benefits**:
- Lower latency
- High availability
- Compliance (GDPR)

#### 12. Advanced Monitoring
**Improvements**:
- APM integration (New Relic, Datadog)
- Error tracking (Sentry)
- Log aggregation (ELK, Loki)
- Alerting (PagerDuty)

**Benefits**:
- Proactive issue detection
- Root cause analysis
- Performance optimization

### Low Priority (Nice to Have)

#### 13. WebSocket Support
- Real-time weather updates
- Streaming API
- Push notifications

#### 14. Batch API
- Request multiple cities at once
- Bulk operations
- Reduced API calls

#### 15. Client SDKs
- Python SDK
- JavaScript/TypeScript SDK
- CLI tool
- Auto-generated from OpenAPI

#### 16. Admin Dashboard
- Web UI for monitoring
- Cache management
- User management
- Analytics dashboard

#### 17. Data Export
- Export metrics to S3
- CSV/JSON data dumps
- Backup/restore functionality

#### 18. Machine Learning
- Weather prediction
- Anomaly detection
- Usage pattern analysis
- Smart caching decisions

### Technical Debt to Address

#### 1. Test Coverage
- Fix 2 failing unit tests (async mocking issues)
- Add more edge case tests
- Performance/load testing
- Chaos engineering tests

#### 2. Documentation
- More code comments
- Architecture diagrams
- Sequence diagrams
- Video tutorials

#### 3. CI/CD Pipeline
- GitHub Actions workflow
- Automated testing
- Container scanning
- Automated deployment

#### 4. Performance Optimization
- Query optimization
- Connection pooling
- Async improvements
- Caching layer optimization

#### 5. Security Hardening
- Security scanning (Snyk, Trivy)
- Dependency updates
- Secret management (Vault)
- Network policies

---

## Documentation

### Main Documentation
- **README.md** (this file) - Overview and setup
- **DOCKER_COMPOSE_GUIDE.md** - Docker Compose detailed guide
- **HELM_DEPLOYMENT.md** - Kubernetes/Helm deployment
- **CI_CD.md** - CI/CD pipeline documentation
- **INTEGRATION_TESTS.md** - Integration testing guide

### Technical Documentation
- **EMBEDDED_REDIS.md** - Embedded Redis feature documentation
- **DOCKER_EMBEDDED_REDIS.md** - Quick reference for embedded Redis
- **GRACEFUL_SHUTDOWN.md** - Graceful shutdown implementation
- **HELM_CHART_SUMMARY.md** - Helm chart overview

### API Documentation
- **OpenAPI Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative UI)
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Project Structure

```
weather-proxy/
├── main.py                          # Main application
├── test_main.py                     # Unit tests
├── test_integration.py              # Integration tests
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Pytest configuration
│
├── Dockerfile                       # Docker image definition
├── docker-entrypoint.sh            # Container entrypoint script
├── .dockerignore                    # Docker build exclusions
│
├── docker-compose.yml               # Default compose config
├── docker-compose.dev.yml           # Development config
├── docker-compose.external-redis.yml # External Redis config
├── docker-compose.prod.yml          # Production config
├── redis.conf                       # Redis configuration
├── nginx.conf                       # Nginx configuration
├── env.example                      # Environment template
│
├── .github/                         # CI/CD configuration
│   └── workflows/
│       └── ci.yml                   # GitHub Actions pipeline
│
├── helm/                            # Helm chart
│   ├── weather-proxy/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-production.yaml
│   │   ├── values-staging.yaml
│   │   └── templates/
│   ├── install.sh                   # Installation script
│   ├── HELM_DEPLOYMENT.md
│   └── HELM_CHART_SUMMARY.md
│
└── docs/                            # Documentation
    ├── README.md                    # This file
    ├── CI_CD.md                     # CI/CD pipeline guide
    ├── DOCKER_COMPOSE_GUIDE.md
    ├── EMBEDDED_REDIS.md
    ├── DOCKER_EMBEDDED_REDIS.md
    ├── GRACEFUL_SHUTDOWN.md
    └── INTEGRATION_TESTS.md
```

---

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run tests: `pytest`
5. Lint code: `flake8 main.py`
6. Submit pull request

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests for new features

---

## License

[Specify your license here]

---

## Support

### Issues & Questions
- **GitHub Issues**: https://github.com/tomertea-arch/weather-proxy/issues
- **Email**: trivish@hotmail.com

### Useful Commands

```bash
# Health check
curl http://localhost:8000/health | jq .

# View logs
docker logs -f weather-proxy
# or
kubectl logs -f deployment/weather-proxy

# Check metrics
curl http://localhost:8000/metrics | grep weather_proxy

# Test endpoints
curl "http://localhost:8000/weather?city=Tokyo"
```

---

**Built with ❤️ by Tomer Traivish**

**Version**: 1.0.0  
**Last Updated**: January 22, 2026  
**Status**: ✅ Production Ready
