"""
FastAPI Proxy Microservice with Redis caching
Optimized for AWS Fargate deployment
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
import redis
import os
import json
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler

# Configure logging to file and console
log_file = os.getenv("LOG_FILE", "weather-proxy.log")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Create formatters
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_formatter = logging.Formatter(
    '%(levelname)s - %(message)s'
)

# File handler with rotation (10MB max, 5 backup files)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent duplicate logs
logger.propagate = False

# Initialize FastAPI app
app = FastAPI(
    title="Weather Proxy Service",
    description="Proxy microservice with Redis caching and Open-Meteo weather API integration",
    version="1.0.0"
)

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

# Metrics tracking
class Metrics:
    """Simple in-memory metrics tracking"""
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.requests_by_endpoint = {}
    
    def increment_request(self, endpoint: str = "unknown"):
        self.request_count += 1
        self.requests_by_endpoint[endpoint] = self.requests_by_endpoint.get(endpoint, 0) + 1
    
    def increment_error(self):
        self.error_count += 1
    
    def get_stats(self):
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "requests_by_endpoint": self.requests_by_endpoint.copy()
        }

metrics = Metrics()


@app.get("/health")
async def health_check():
    """Health check endpoint for Fargate - returns service health, metrics, and Redis status"""
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
            "requests_by_endpoint": stats["requests_by_endpoint"]
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
    
    # Log health check request
    logger.info(f"Health check: status={health_status['status']}, redis={redis_status}, "
                f"requests={stats['total_requests']}, errors={stats['total_errors']}")
    
    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    metrics.increment_request("/")
    logger.info("Root endpoint accessed")
    return {
        "service": "weather-proxy",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/weather")
async def get_weather(city: str):
    """
    Get weather data for a city.
    Returns cached data from Redis if available, otherwise fetches from Open-Meteo API.
    """
    metrics.increment_request("/weather")
    
    if not city:
        metrics.increment_error()
        raise HTTPException(status_code=400, detail="City parameter is required")
    
    # Normalize city name for cache key (lowercase, strip whitespace)
    city_normalized = city.strip().lower()
    cache_key = f"weather:{city_normalized}"
    
    # Check Redis cache first
    if redis_client:
        try:
            cached_weather = redis_client.get(cache_key)
            if cached_weather:
                logger.info(f"Cache hit for city: {city}")
                weather_result = json.loads(cached_weather)
                weather_result["cached"] = True
                return weather_result
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    # Fetch fresh data from Open-Meteo
    try:
        # Step 1: Geocode the city to get coordinates
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocode_params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        logger.info(f"Fetching coordinates for city: {city}")
        geocode_response = await http_client.get(geocode_url, params=geocode_params)
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()
        
        if not geocode_data.get("results") or len(geocode_data["results"]) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"City '{city}' not found"
            )
        
        location = geocode_data["results"][0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")
        
        # Step 2: Fetch weather data using coordinates
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
            "timezone": "auto"
        }
        
        logger.info(f"Fetching weather for {city_name} ({latitude}, {longitude})")
        weather_response = await http_client.get(weather_url, params=weather_params)
        weather_response.raise_for_status()
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
        
        # Cache the result in Redis (cache for 10 minutes = 600 seconds)
        # Don't store "cached" field in cache
        if redis_client:
            try:
                redis_client.setex(cache_key, 600, json.dumps(result))
                logger.info(f"Cached weather data for city: {city}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        # Add cached flag for fresh data
        result["cached"] = False
        return result
        
    except httpx.HTTPStatusError as e:
        metrics.increment_error()
        logger.error(f"HTTP error fetching weather: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error fetching weather data: {str(e)}"
        )
    except httpx.RequestError as e:
        metrics.increment_error()
        logger.error(f"Request error fetching weather: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Error connecting to weather service: {str(e)}"
        )
    except HTTPException:
        metrics.increment_error()
        raise
    except Exception as e:
        metrics.increment_error()
        logger.error(f"Unexpected error fetching weather: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(path: str, request: Request):
    """
    Proxy endpoint that caches GET requests in Redis
    """
    metrics.increment_request(f"/proxy/{request.method}")
    
    # Get target URL from query parameter or header
    target_url = request.query_params.get("url")
    if not target_url:
        metrics.increment_error()
        raise HTTPException(status_code=400, detail="Missing 'url' query parameter")
    
    # Build full URL
    if not target_url.startswith("http"):
        target_url = f"https://{target_url}"
    
    # For GET requests, check cache
    cache_key = None
    if request.method == "GET" and redis_client:
        cache_key = f"proxy:{target_url}:{path}"
        try:
            cached_response = redis_client.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {cache_key}")
                cached_data = json.loads(cached_response)
                return JSONResponse(
                    content=cached_data["content"],
                    status_code=cached_data["status_code"],
                    headers=cached_data.get("headers", {})
                )
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    # Make proxied request
    try:
        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
        
        # Forward headers (excluding host and connection)
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("connection", None)
        
        # Make request
        response = await http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params
        )
        
        # Prepare response
        response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text
        }
        
        # Cache GET responses
        if request.method == "GET" and redis_client and cache_key and response.status_code == 200:
            try:
                # Cache for 5 minutes (300 seconds)
                redis_client.setex(cache_key, 300, json.dumps(response_data))
                logger.info(f"Cached response for {cache_key}")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        return JSONResponse(
            content=response_data,
            status_code=response.status_code
        )
        
    except httpx.RequestError as e:
        metrics.increment_error()
        logger.error(f"Proxy request error: {e}")
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")
    except Exception as e:
        metrics.increment_error()
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    await http_client.aclose()
    if redis_client:
        redis_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
