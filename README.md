# Weather Proxy Microservice

A FastAPI-based proxy microservice with Redis caching, optimized for AWS Fargate deployment.

## Features

- FastAPI framework for high-performance async requests
- Redis integration for response caching
- Health check endpoint for Fargate health monitoring
- Non-root user for enhanced security
- Optimized Docker image for Fargate

## Environment Variables

- `REDIS_HOST`: Redis server hostname (default: localhost)
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password (optional)

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

- `GET /health` - Health check endpoint
- `GET /` - Service info
- `GET /weather?city={city_name}` - Get weather data for a city (cached in Redis)
- `GET /proxy/{path}?url=<target_url>` - Proxy GET request with caching
- `POST /proxy/{path}?url=<target_url>` - Proxy POST request
- Other HTTP methods supported via `/proxy/{path}`

## Example Usage

```bash
# Get weather for a city (will cache for 10 minutes)
curl "http://localhost:8000/weather?city=London"

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
