# Weather Proxy Microservice

A FastAPI-based proxy microservice with Redis caching, optimized for AWS Fargate deployment.

## Features

- FastAPI framework for high-performance async requests
- Redis integration for response caching
- Health check endpoint with metrics (request count, errors, duration, upstream status codes)
- **Retry mechanism with exponential backoff** for weather API calls (up to 3 attempts)
- **Graceful shutdown handling** with SIGTERM/SIGINT signal support
- Request duration and upstream status code logging
- Prometheus-compatible `/metrics` endpoint for monitoring
- Non-root user for enhanced security
- Optimized Docker image for Fargate

## Environment Variables

- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password (optional)
- `LOG_FILE`: Log file path (default: weather-proxy.log)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)

## Graceful Shutdown

The application implements proper graceful shutdown handling for containerized environments:

### Signal Handling
- **SIGTERM**: Sent by Kubernetes/Fargate/Docker when stopping a container
- **SIGINT**: Sent when pressing Ctrl+C (useful for local development)

### Shutdown Process
1. Signal handler receives SIGTERM/SIGINT
2. Logs the shutdown initiation
3. Waits 2 seconds for in-flight requests to complete
4. Closes HTTP client connections gracefully
5. Closes Redis connections
6. Uvicorn waits up to 10 seconds for final cleanup (configurable via `--timeout-graceful-shutdown`)

### Benefits for AWS Fargate
- Prevents connection errors during deployments
- Ensures requests complete before container termination
- Proper cleanup of resources (connections, file handles)
- Compliance with the Fargate task stop behavior (30-second default stop timeout)

### Testing Graceful Shutdown Locally
```bash
# Start the application
docker run -p 8000:8000 weather-proxy:latest

# In another terminal, send SIGTERM
docker kill --signal=SIGTERM <container-id>

# Check logs for shutdown messages
docker logs <container-id>
```

## Building the Docker Image

```bash
docker build -t weather-proxy:latest .
```

## Running Locally

```bash
docker run -p 8000:8000 \
  -e REDIS_HOST=your-redis-host \
  -e REDIS_PORT=6379 \
  weather-proxy:latest
```

## AWS Fargate Deployment

1. Build and push to ECR:
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t weather-proxy .
docker tag weather-proxy:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/weather-proxy:latest
```

2. Configure Fargate task with:
   - Port mapping: 8000
   - Health check: GET /health
   - Environment variables for Redis connection

## API Endpoints

- `GET /health` - Health check with metrics (service status, request count, error count, Redis status)
- `GET /metrics` - **Prometheus metrics endpoint** (request latency, counts, cache operations, upstream status codes)
- `GET /` - Service info
- `GET /weather?city={city_name}` - Get weather data for a city (cached in Redis)
- `GET /proxy/{path}?url=<target_url>` - Proxy GET request with caching
- `POST /proxy/{path}?url=<target_url>` - Proxy POST request
- Other HTTP methods supported via `/proxy/{path}`

### Health Endpoint Response

```json
{
  "status": "healthy",
  "service": "weather-proxy",
  "metrics": {
    "total_requests": 150,
    "total_errors": 2,
    "requests_by_endpoint": {
      "/health": 10,
      "/weather": 100,
      "/proxy/GET": 40
    },
    "request_duration": {
      "avg_ms": 45.32,
      "min_ms": 5.21,
      "max_ms": 523.45,
      "count": 150
    },
    "upstream_status_codes": {
      "200": 145,
      "404": 3,
      "500": 2
    }
  },
  "redis": {
    "status": "connected",
    "host": "localhost",
    "port": 6379
  }
}
```

### Logged Metrics

All requests log the following key metrics:
- **Request duration**: Time taken to process the request (in milliseconds)
- **Upstream status codes**: HTTP status codes received from upstream services (Open-Meteo API, proxied targets)
- **Cache hits/misses**: Whether the response was served from Redis cache
- **Retry attempts**: Number of retry attempts for failed requests (logged with WARNING level)

Example log entries:
```
INFO - Weather request completed: city=London, duration=234.56ms, cached=False
INFO - Weather API response: status=200, attempt=1
INFO - Proxy request completed: method=GET, url=https://api.example.com, upstream_status=200, duration=156.78ms
INFO - Cache hit for weather:london, duration=2.34ms
WARNING - Retry attempt 2 for city: Paris
WARNING - Retrying in 2.0 seconds...
INFO - Weather fetch succeeded after 2 attempts for city: Paris
ERROR - Weather fetch failed after 3 attempts for city: InvalidCity, error=...
```

### Retry Mechanism

The weather endpoint implements an automatic retry mechanism with exponential backoff:
- **Max attempts**: 3
- **Backoff strategy**: Exponential (1s, 2s, 4s, up to 10s max)
- **Retryable errors**: Network errors (RequestError), HTTP errors (HTTPStatusError)
- **Non-retryable**: 404 Not Found (city doesn't exist)

This provides resilience against transient network issues and temporary API unavailability.

## Prometheus Metrics Endpoint

The `/metrics` endpoint exposes metrics in Prometheus format for monitoring and alerting:

```bash
curl http://localhost:8000/metrics
```

### Available Metrics:

**Request Metrics:**
- `weather_proxy_requests_total` - Total requests by endpoint, method, and status
- `weather_proxy_request_duration_seconds` - Request latency histogram (percentiles: p50, p95, p99)

**Error Metrics:**
- `weather_proxy_errors_total` - Total errors by endpoint and error type

**Upstream Metrics:**
- `weather_proxy_upstream_status_total` - Upstream service status codes (Open-Meteo API, etc.)

**Cache Metrics:**
- `weather_proxy_cache_operations_total` - Cache hit/miss/error counts
- `weather_proxy_redis_connected` - Redis connection status (1=connected, 0=disconnected)

Example Prometheus scrape config:
```yaml
scrape_configs:
  - job_name: 'weather-proxy'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Example Usage

```bash
# Get weather for a city (will cache for 10 minutes)
curl "http://localhost:8000/weather?city=London"

# View Prometheus metrics
curl "http://localhost:8000/metrics"

# Proxy a GET request (cached)
curl "http://localhost:8000/proxy/api?url=https://api.example.com/data"

# Proxy a POST request
curl -X POST "http://localhost:8000/proxy/api?url=https://api.example.com/data" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

## Running Tests

Install test dependencies:
```bash
pip install -r requirements.txt
```

Run all tests:
```bash
pytest
```

Run tests with verbose output:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest test_main.py
```

Run a specific test:
```bash
pytest test_main.py::TestWeatherEndpoint::test_weather_fresh_data_no_cache
```

## Test Coverage

The test suite includes:
- Health check endpoint tests (with/without Redis)
- Root endpoint tests
- Weather endpoint tests (cached/fresh data, error handling)
- Proxy endpoint tests (GET/POST, caching)
- Error handling and edge cases
