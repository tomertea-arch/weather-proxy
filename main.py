"""
FastAPI Proxy Microservice with Redis caching
Optimized for AWS Fargate deployment
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import redis
import os
import json
import time
import signal
import asyncio
import uuid
from typing import Optional
from contextlib import asynccontextmanager
from contextvars import ContextVar
import logging
from logging.handlers import RotatingFileHandler
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry
)

# Request ID context variable for tracing
request_id_context: ContextVar[str] = ContextVar('request_id', default='no-request-id')


class RequestIDFilter(logging.Filter):
    """Logging filter to inject request_id into all log records"""
    
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True


# Configure logging to file and console
log_file = os.getenv("LOG_FILE", "weather-proxy.log")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Create formatters with request_id
file_formatter = logging.Formatter(
    '%(asctime)s - [%(request_id)s] - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_formatter = logging.Formatter(
    '[%(request_id)s] - %(levelname)s - %(message)s'
)

# File handler with rotation (10MB max, 5 backup files)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)
file_handler.addFilter(RequestIDFilter())

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)
console_handler.addFilter(RequestIDFilter())

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent duplicate logs
logger.propagate = False

# Shutdown event for graceful shutdown
shutdown_event = asyncio.Event()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and inject a unique request ID for each request.
    The request ID is propagated through all logs for request tracing.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID from header
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Set request ID in context for logging
        request_id_context.set(request_id)
        
        # Store in request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers for client tracking
        response.headers['X-Request-ID'] = request_id
        
        return response


# Lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for graceful startup and shutdown.
    Handles resource initialization and cleanup.
    """
    # Startup
    logger.info("Application starting up...")
    
    # Setup signal handlers for graceful shutdown
    def handle_shutdown_signal(signum, frame):
        """Handle SIGTERM and SIGINT signals"""
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    logger.info("Signal handlers registered for SIGTERM and SIGINT")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down gracefully...")
    
    # Wait a brief moment for in-flight requests to complete
    logger.info("Waiting for in-flight requests to complete...")
    await asyncio.sleep(2)  # Grace period for in-flight requests
    
    # Close HTTP client
    try:
        await http_client.aclose()
        logger.info("HTTP client closed successfully")
    except Exception as e:
        logger.error(f"Error closing HTTP client: {e}")
    
    # Close Redis connection
    if redis_client:
        try:
            redis_client.close()
            logger.info("Redis client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Redis client: {e}")
    
    logger.info("Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Weather Proxy Service",
    description="Proxy microservice with Redis caching and Open-Meteo weather API integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add Request ID middleware
app.add_middleware(RequestIDMiddleware)

# Redis connection configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Running without cache.")
    redis_client = None

# HTTP client for proxying requests
http_client = httpx.AsyncClient(timeout=30.0)

# Prometheus metrics
prometheus_registry = CollectorRegistry()

# Request count by endpoint and method
request_count = Counter(
    'weather_proxy_requests_total',
    'Total number of requests',
    ['endpoint', 'method', 'status'],
    registry=prometheus_registry
)

# Request latency histogram
request_latency = Histogram(
    'weather_proxy_request_duration_seconds',
    'Request latency in seconds',
    ['endpoint', 'method'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=prometheus_registry
)

# Upstream status codes
upstream_status_count = Counter(
    'weather_proxy_upstream_status_total',
    'Upstream response status codes',
    ['service', 'status_code'],
    registry=prometheus_registry
)

# Error count
error_count = Counter(
    'weather_proxy_errors_total',
    'Total number of errors',
    ['endpoint', 'error_type'],
    registry=prometheus_registry
)

# Redis connection status
redis_status = Gauge(
    'weather_proxy_redis_connected',
    'Redis connection status (1=connected, 0=disconnected)',
    registry=prometheus_registry
)

# Cache hit/miss counter
cache_operations = Counter(
    'weather_proxy_cache_operations_total',
    'Cache operations',
    ['operation', 'result'],
    registry=prometheus_registry
)

# Update Redis status
if redis_client:
    try:
        redis_client.ping()
        redis_status.set(1)
    except:
        redis_status.set(0)
else:
    redis_status.set(0)

# Metrics tracking
class Metrics:
    """Simple in-memory metrics tracking"""
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.requests_by_endpoint = {}
        self.request_durations = []  # Store last N request durations
        self.upstream_status_codes = {}  # Track upstream response status codes
        self.max_duration_samples = 1000  # Keep last 1000 samples
    
    def increment_request(self, endpoint: str = "unknown"):
        self.request_count += 1
        self.requests_by_endpoint[endpoint] = self.requests_by_endpoint.get(endpoint, 0) + 1
    
    def increment_error(self):
        self.error_count += 1
    
    def record_duration(self, duration_ms: float):
        """Record request duration in milliseconds"""
        self.request_durations.append(duration_ms)
        # Keep only last N samples
        if len(self.request_durations) > self.max_duration_samples:
            self.request_durations = self.request_durations[-self.max_duration_samples:]
    
    def record_upstream_status(self, status_code: int):
        """Record upstream response status code"""
        key = str(status_code)
        self.upstream_status_codes[key] = self.upstream_status_codes.get(key, 0) + 1
    
    def get_duration_stats(self):
        """Calculate duration statistics"""
        if not self.request_durations:
            return {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "count": 0}
        
        return {
            "avg_ms": round(sum(self.request_durations) / len(self.request_durations), 2),
            "min_ms": round(min(self.request_durations), 2),
            "max_ms": round(max(self.request_durations), 2),
            "count": len(self.request_durations)
        }
    
    def get_stats(self):
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "requests_by_endpoint": self.requests_by_endpoint.copy(),
            "request_duration": self.get_duration_stats(),
            "upstream_status_codes": self.upstream_status_codes.copy()
        }

metrics = Metrics()


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus exposition format.
    """
    # Update Redis connection status
    if redis_client:
        try:
            redis_client.ping()
            redis_status.set(1)
        except:
            redis_status.set(0)
    
    # Generate Prometheus metrics
    metrics_output = generate_latest(prometheus_registry)
    return Response(content=metrics_output, media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health_check():
    """Health check endpoint for Fargate - returns service health, metrics, and Redis status"""
    start_time = time.time()
    
    # Track this request
    metrics.increment_request("/health")
    
    # Get metrics stats
    stats = metrics.get_stats()
    
    health_status = {
        "status": "healthy",
        "service": "weather-proxy",
        "metrics": {
            "total_requests": stats["total_requests"],
            "total_errors": stats["total_errors"],
            "requests_by_endpoint": stats["requests_by_endpoint"],
            "request_duration": stats["request_duration"],
            "upstream_status_codes": stats["upstream_status_codes"]
        }
    }
    
    # Check Redis connection
    redis_status = "not_configured"
    if redis_client:
        try:
            redis_client.ping()
            redis_status = "connected"
            health_status["redis"] = {
                "status": "connected",
                "host": REDIS_HOST,
                "port": REDIS_PORT
            }
        except Exception as e:
            redis_status = "disconnected"
            health_status["redis"] = {
                "status": "disconnected",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["redis"] = {
            "status": "not_configured"
        }
    
    # Log health check request with key metrics
    duration_stats = stats["request_duration"]
    logger.info(f"Health check: status={health_status['status']}, redis={redis_status}, "
                f"requests={stats['total_requests']}, errors={stats['total_errors']}, "
                f"avg_duration={duration_stats['avg_ms']}ms, upstream_codes={stats['upstream_status_codes']}")
    
    # Track in Prometheus
    duration_ms = (time.time() - start_time) * 1000
    request_latency.labels(endpoint='/health', method='GET').observe(duration_ms / 1000)
    request_count.labels(endpoint='/health', method='GET', status='200').inc()
    
    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    start_time = time.time()
    metrics.increment_request("/")
    logger.info("Root endpoint accessed")
    
    # Track in Prometheus
    duration_ms = (time.time() - start_time) * 1000
    request_latency.labels(endpoint='/', method='GET').observe(duration_ms / 1000)
    request_count.labels(endpoint='/', method='GET', status='200').inc()
    
    return {
        "service": "weather-proxy",
        "status": "running",
        "version": "1.0.0"
    }


async def fetch_weather_with_retry(city: str, cache_key: str, start_time: float):
    """
    Fetch weather data with retry mechanism for resilience.
    Uses exponential backoff retry on transient errors.
    """
    retry_count = {"attempts": 0}
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _fetch_with_retry():
        retry_count["attempts"] += 1
        attempt_num = retry_count["attempts"]
        
        if attempt_num > 1:
            logger.warning(f"[RETRY] Attempt {attempt_num} for city: {city}")
        
        # Step 1: Geocode the city to get coordinates
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocode_params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        logger.info(f"[GEOCODE] Fetching coordinates for city: {city} (attempt {attempt_num})")
        geocode_response = await http_client.get(geocode_url, params=geocode_params)
        geocode_response.raise_for_status()
        geocode_status = geocode_response.status_code
        metrics.record_upstream_status(geocode_status)
        upstream_status_count.labels(service='open-meteo-geocoding', status_code=str(geocode_status)).inc()
        logger.info(f"[GEOCODE] Response received: status={geocode_status}, attempt={attempt_num}")
        geocode_data = geocode_response.json()
        
        if not geocode_data.get("results") or len(geocode_data["results"]) == 0:
            logger.warning(f"[GEOCODE] City not found: {city}")
            raise HTTPException(
                status_code=404,
                detail=f"City '{city}' not found"
            )
        
        location = geocode_data["results"][0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")
        
        logger.debug(f"[GEOCODE] Found: {city_name}, {country} at ({latitude}, {longitude})")
        
        # Step 2: Fetch weather data using coordinates
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
            "timezone": "auto"
        }
        
        logger.info(f"[WEATHER API] Fetching data for {city_name} ({latitude}, {longitude}) (attempt {attempt_num})")
        weather_response = await http_client.get(weather_url, params=weather_params)
        weather_response.raise_for_status()
        weather_status = weather_response.status_code
        metrics.record_upstream_status(weather_status)
        upstream_status_count.labels(service='open-meteo-weather', status_code=str(weather_status)).inc()
        logger.info(f"[WEATHER API] Response received: status={weather_status}, attempt={attempt_num}")
        weather_data = weather_response.json()
        
        # Combine location and weather data
        result = {
            "city": city_name,
            "country": country,
            "coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "current_weather": weather_data.get("current_weather", {}),
            "timezone": weather_data.get("timezone", "")
        }
        
        return result
    
    try:
        result = await _fetch_with_retry()
        
        # Cache the result in Redis (cache for 10 minutes = 600 seconds)
        if redis_client:
            try:
                redis_client.setex(cache_key, 600, json.dumps(result))
                logger.info(f"[CACHE WRITE] Stored weather data for city: {city}, TTL=600s")
            except Exception as e:
                logger.warning(f"[CACHE WRITE] Error storing cache: {e}")
        
        # Log successful completion with retry count
        if retry_count["attempts"] > 1:
            logger.info(f"[SUCCESS] Fetch succeeded after {retry_count['attempts']} attempts for city: {city}")
        else:
            logger.info(f"[SUCCESS] Fetch completed on first attempt for city: {city}")
        
        return result
    
    except Exception as e:
        logger.error(f"[FETCH FAILED] Failed after {retry_count['attempts']} attempts for city: {city}, error={e}")
        raise


@app.get("/weather")
async def get_weather(city: str, request: Request):
    """
    Get weather data for a city.
    Returns cached data from Redis if available, otherwise fetches from Open-Meteo API.
    Implements retry mechanism with exponential backoff for transient failures.
    Each request is traced with a unique request_id for debugging.
    """
    start_time = time.time()
    metrics.increment_request("/weather")
    
    # Get request ID from state
    request_id = request.state.request_id
    
    logger.info(f"[START] Weather request for city: {city}")
    
    if not city:
        metrics.increment_error()
        logger.error("City parameter is missing")
        raise HTTPException(status_code=400, detail="City parameter is required")
    
    # Normalize city name for cache key (lowercase, strip whitespace)
    city_normalized = city.strip().lower()
    cache_key = f"weather:{city_normalized}"
    
    # Check Redis cache first
    if redis_client:
        try:
            logger.debug(f"Checking cache for key: {cache_key}")
            cached_weather = redis_client.get(cache_key)
            if cached_weather:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_duration(duration_ms)
                logger.info(f"[CACHE HIT] City: {city}, duration={duration_ms:.2f}ms")
                
                # Track Prometheus metrics
                cache_operations.labels(operation='get', result='hit').inc()
                request_latency.labels(endpoint='/weather', method='GET').observe(duration_ms / 1000)
                request_count.labels(endpoint='/weather', method='GET', status='200').inc()
                
                weather_result = json.loads(cached_weather)
                weather_result["cached"] = True
                weather_result["request_id"] = request_id
                logger.info(f"[END] Request completed successfully (cached)")
                return weather_result
            else:
                logger.info(f"[CACHE MISS] City: {city}, fetching from API")
                cache_operations.labels(operation='get', result='miss').inc()
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            cache_operations.labels(operation='get', result='error').inc()
    
    # Fetch fresh data from Open-Meteo with retry mechanism
    try:
        logger.info(f"[FETCH] Starting API fetch for city: {city}")
        result = await fetch_weather_with_retry(city, cache_key, start_time)
        
        # Record request duration
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_duration(duration_ms)
        logger.info(f"[API SUCCESS] City: {city}, duration={duration_ms:.2f}ms")
        
        # Track Prometheus metrics
        request_latency.labels(endpoint='/weather', method='GET').observe(duration_ms / 1000)
        request_count.labels(endpoint='/weather', method='GET', status='200').inc()
        
        # Add cached flag and request ID for fresh data
        result["cached"] = False
        result["request_id"] = request_id
        logger.info(f"[END] Request completed successfully (fresh data)")
        return result
        
    except httpx.HTTPStatusError as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_duration(duration_ms)
        metrics.increment_error()
        metrics.record_upstream_status(e.response.status_code)
        
        # Track Prometheus metrics
        request_latency.labels(endpoint='/weather', method='GET').observe(duration_ms / 1000)
        request_count.labels(endpoint='/weather', method='GET', status=str(e.response.status_code)).inc()
        error_count.labels(endpoint='/weather', error_type='http_error').inc()
        
        logger.error(f"[ERROR] HTTP error: city={city}, status={e.response.status_code}, error={e}, duration={duration_ms:.2f}ms")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error fetching weather data: {str(e)}"
        )
    except httpx.RequestError as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_duration(duration_ms)
        metrics.increment_error()
        
        # Track Prometheus metrics
        request_latency.labels(endpoint='/weather', method='GET').observe(duration_ms / 1000)
        request_count.labels(endpoint='/weather', method='GET', status='502').inc()
        error_count.labels(endpoint='/weather', error_type='request_error').inc()
        
        logger.error(f"[ERROR] Request error: city={city}, error={e}, duration={duration_ms:.2f}ms")
        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to weather service: {str(e)}"
        )
    except HTTPException as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_duration(duration_ms)
        metrics.increment_error()
        
        # Track Prometheus metrics
        request_latency.labels(endpoint='/weather', method='GET').observe(duration_ms / 1000)
        request_count.labels(endpoint='/weather', method='GET', status=str(e.status_code)).inc()
        error_count.labels(endpoint='/weather', error_type='http_exception').inc()
        
        logger.error(f"[ERROR] HTTP exception: city={city}, status={e.status_code}")
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics.record_duration(duration_ms)
        metrics.increment_error()
        
        # Track Prometheus metrics
        request_latency.labels(endpoint='/weather', method='GET').observe(duration_ms / 1000)
        request_count.labels(endpoint='/weather', method='GET', status='500').inc()
        error_count.labels(endpoint='/weather', error_type='internal_error').inc()
        
        logger.error(f"[ERROR] Unexpected error: city={city}, error={e}, duration={duration_ms:.2f}ms")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Configure uvicorn for graceful shutdown
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        timeout_graceful_shutdown=10  # Allow 10 seconds for graceful shutdown
    )
