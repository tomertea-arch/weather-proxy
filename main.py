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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Weather Proxy Service",
    description="Proxy microservice with Redis caching",
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


@app.get("/health")
async def health_check():
    """Health check endpoint for Fargate"""
    health_status = {
        "status": "healthy",
        "service": "weather-proxy"
    }
    
    # Check Redis connection
    if redis_client:
        try:
            redis_client.ping()
            health_status["redis"] = "connected"
        except Exception as e:
            health_status["redis"] = f"disconnected: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["redis"] = "not_configured"
    
    return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "weather-proxy",
        "status": "running",
        "version": "1.0.0"
    }


@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(path: str, request: Request):
    """
    Proxy endpoint that caches GET requests in Redis
    """
    # Get target URL from query parameter or header
    target_url = request.query_params.get("url")
    if not target_url:
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
        logger.error(f"Proxy request error: {e}")
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")
    except Exception as e:
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
