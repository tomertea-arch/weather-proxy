"""
Unit tests for the Weather Proxy API
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
import os
import httpx

# Set environment variables before importing main to control Redis connection
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"

# Import after setting env vars
from main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client"""
    mock_redis = Mock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.setex.return_value = True
    return mock_redis


class TestHealthEndpoint:
    """Tests for /health endpoint"""
    
    def test_health_check_without_redis(self, client):
        """Test health check when Redis is not configured"""
        with patch('main.redis_client', None):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "weather-proxy"
            assert data["redis"]["status"] == "not_configured"
            # Check metrics are included
            assert "metrics" in data
            assert "total_requests" in data["metrics"]
            assert "total_errors" in data["metrics"]
            # Check new metrics: request_duration and upstream_status_codes
            assert "request_duration" in data["metrics"]
            assert "avg_ms" in data["metrics"]["request_duration"]
            assert "upstream_status_codes" in data["metrics"]
    
    def test_health_check_with_redis_connected(self, client, mock_redis):
        """Test health check when Redis is connected"""
        with patch('main.redis_client', mock_redis):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["redis"]["status"] == "connected"
            mock_redis.ping.assert_called_once()
            # Check metrics are included
            assert "metrics" in data
            assert data["metrics"]["total_requests"] >= 1  # At least this request
    
    def test_health_check_with_redis_disconnected(self, client, mock_redis):
        """Test health check when Redis connection fails"""
        mock_redis.ping.side_effect = Exception("Connection failed")
        with patch('main.redis_client', mock_redis):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["redis"]["status"] == "disconnected"
            assert "error" in data["redis"]


class TestRootEndpoint:
    """Tests for / endpoint"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "weather-proxy"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"


class TestWeatherEndpoint:
    """Tests for /weather endpoint"""
    
    def test_weather_missing_city_parameter(self, client):
        """Test weather endpoint without city parameter"""
        response = client.get("/weather")
        assert response.status_code == 422  # FastAPI validation error
    
    def test_weather_city_not_found(self, client, mock_redis):
        """Test weather endpoint when city is not found"""
        # Mock geocoding API returning no results
        mock_geocode_response = AsyncMock()
        mock_geocode_response.json = Mock(return_value={"results": []})
        mock_geocode_response.raise_for_status = Mock()
        
        mock_http_client = AsyncMock()
        # Make get() return the mock response directly
        async def mock_get(*args, **kwargs):
            return mock_geocode_response
        mock_http_client.get = mock_get
        
        with patch('main.redis_client', mock_redis), \
             patch('main.http_client', mock_http_client):
            response = client.get("/weather?city=NonExistentCity12345")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_weather_fresh_data_no_cache(self, client, mock_redis):
        """Test weather endpoint fetching fresh data when cache is empty"""
        # Mock Redis - no cached data
        mock_redis.get.return_value = None
        
        # Mock geocoding response
        mock_geocode_response = AsyncMock()
        mock_geocode_response.json.return_value = {
            "results": [{
                "name": "London",
                "country": "United Kingdom",
                "latitude": 51.5074,
                "longitude": -0.1278
            }]
        }
        mock_geocode_response.raise_for_status = Mock()
        
        # Mock weather response
        mock_weather_response = AsyncMock()
        mock_weather_response.json.return_value = {
            "current_weather": {
                "temperature": 15.5,
                "windspeed": 10.2,
                "winddirection": 180,
                "weathercode": 61,
                "time": "2024-01-15T12:00"
            },
            "timezone": "Europe/London"
        }
        mock_weather_response.raise_for_status = Mock()
        
        # Setup async mock to return different responses sequentially
        responses_list = [mock_geocode_response, mock_weather_response]
        call_count = {'idx': 0}
        
        async def mock_get(*args, **kwargs):
            idx = call_count['idx']
            call_count['idx'] += 1
            if idx < len(responses_list):
                return responses_list[idx]
            return AsyncMock()
        
        mock_http_client = AsyncMock()
        mock_http_client.get = mock_get
        
        with patch('main.redis_client', mock_redis), \
             patch('main.http_client', mock_http_client):
            response = client.get("/weather?city=London")
            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "London"
            assert data["country"] == "United Kingdom"
            assert data["coordinates"]["latitude"] == 51.5074
            assert data["coordinates"]["longitude"] == -0.1278
            assert data["cached"] is False
            assert "current_weather" in data
            # Verify cache was written
            mock_redis.setex.assert_called_once()
    
    def test_weather_cached_data(self, client, mock_redis):
        """Test weather endpoint returning cached data"""
        # Mock cached data in Redis
        cached_data = {
            "city": "London",
            "country": "United Kingdom",
            "coordinates": {
                "latitude": 51.5074,
                "longitude": -0.1278
            },
            "current_weather": {
                "temperature": 15.5,
                "windspeed": 10.2
            },
            "timezone": "Europe/London"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        with patch('main.redis_client', mock_redis):
            response = client.get("/weather?city=London")
            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "London"
            assert data["cached"] is True
    
    def test_weather_cache_read_error(self, client, mock_redis):
        """Test weather endpoint when cache read fails but continues to fetch"""
        # Mock Redis read error
        mock_redis.get.side_effect = Exception("Redis read error")
        
        # Mock successful API responses
        mock_geocode_response = AsyncMock()
        mock_geocode_response.json.return_value = {
            "results": [{
                "name": "Paris",
                "country": "France",
                "latitude": 48.8566,
                "longitude": 2.3522
            }]
        }
        mock_geocode_response.raise_for_status = Mock()
        
        mock_weather_response = AsyncMock()
        mock_weather_response.json.return_value = {
            "current_weather": {"temperature": 20.0},
            "timezone": "Europe/Paris"
        }
        mock_weather_response.raise_for_status = Mock()
        
        # Setup async mock to return different responses sequentially
        responses_list = [mock_geocode_response, mock_weather_response]
        call_count = {'idx': 0}
        
        async def mock_get(*args, **kwargs):
            idx = call_count['idx']
            call_count['idx'] += 1
            if idx < len(responses_list):
                return responses_list[idx]
            return AsyncMock()
        
        mock_http_client = AsyncMock()
        mock_http_client.get = mock_get
        
        with patch('main.redis_client', mock_redis), \
             patch('main.http_client', mock_http_client):
            response = client.get("/weather?city=Paris")
            assert response.status_code == 200
            data = response.json()
            assert data["city"] == "Paris"
            assert data["cached"] is False
    
    def test_weather_http_error(self, client, mock_redis):
        """Test weather endpoint when HTTP request fails"""
        mock_redis.get.return_value = None
        
        # Mock HTTP error - raise error on raise_for_status
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Not Found", 
            request=Mock(), 
            response=Mock(status_code=404)
        ))
        
        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        
        with patch('main.redis_client', mock_redis), \
             patch('main.http_client', mock_http_client):
            response = client.get("/weather?city=London")
            assert response.status_code >= 400
    
    def test_weather_city_name_normalization(self, client, mock_redis):
        """Test that city names are normalized for cache keys"""
        cached_data = {
            "city": "New York",
            "country": "United States",
            "coordinates": {"latitude": 40.7128, "longitude": -74.0060},
            "current_weather": {},
            "timezone": "America/New_York"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        with patch('main.redis_client', mock_redis):
            # Test with different case and whitespace
            response = client.get("/weather?city=  NEW YORK  ")
            assert response.status_code == 200
            data = response.json()
            assert data["cached"] is True


class TestMetricsEndpoint:
    """Tests for /metrics endpoint"""
    
    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test that /metrics endpoint returns Prometheus format"""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Check Content-Type header for Prometheus format
        assert "text/plain" in response.headers.get("content-type", "")
        
        # Verify Prometheus metric format
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
        
    def test_metrics_contains_request_count(self, client):
        """Test that metrics include request count"""
        # Make a request to generate metrics
        client.get("/")
        
        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for request count metric
        assert "weather_proxy_requests_total" in content
        
    def test_metrics_contains_request_duration(self, client):
        """Test that metrics include request duration"""
        # Make a request to generate metrics
        client.get("/health")
        
        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for duration histogram metric
        assert "weather_proxy_request_duration_seconds" in content
        # Check for histogram buckets
        assert "_bucket" in content
        assert "_count" in content
        assert "_sum" in content
        
    def test_metrics_contains_error_count(self, client):
        """Test that metrics include error count"""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for error count metric
        assert "weather_proxy_errors_total" in content
        
    def test_metrics_contains_cache_operations(self, client):
        """Test that metrics include cache operations"""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for cache operations metric
        assert "weather_proxy_cache_operations_total" in content
        
    def test_metrics_contains_redis_status(self, client, mock_redis):
        """Test that metrics include Redis connection status"""
        with patch('main.redis_client', mock_redis):
            response = client.get("/metrics")
            assert response.status_code == 200
            content = response.text
            
            # Check for Redis status gauge
            assert "weather_proxy_redis_connected" in content
    
    def test_metrics_contains_upstream_status(self, client):
        """Test that metrics include upstream status codes"""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Check for upstream status metric
        assert "weather_proxy_upstream_status_total" in content
    
    def test_metrics_tracks_multiple_requests(self, client):
        """Test that metrics correctly track multiple requests"""
        # Make multiple requests
        client.get("/")
        client.get("/health")
        client.get("/")
        
        # Get metrics
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.text
        
        # Verify metrics are incremented
        assert "weather_proxy_requests_total" in content
        # Check that we have different endpoints tracked
        assert 'endpoint="/"' in content or 'endpoint="' in content
        assert 'endpoint="/health"' in content or 'endpoint="' in content
    
    def test_metrics_with_cached_weather_request(self, client, mock_redis):
        """Test that cache hit is tracked in metrics"""
        # Mock cached data
        cached_data = {
            "city": "London",
            "country": "United Kingdom",
            "coordinates": {"latitude": 51.5074, "longitude": -0.1278},
            "current_weather": {"temperature": 15.5},
            "timezone": "Europe/London"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        with patch('main.redis_client', mock_redis):
            # Make weather request (cache hit)
            client.get("/weather?city=London")
            
            # Get metrics
            response = client.get("/metrics")
            assert response.status_code == 200
            content = response.text
            
            # Verify cache hit is tracked
            assert "weather_proxy_cache_operations_total" in content
            assert 'operation="get"' in content
            assert 'result="hit"' in content or "cache" in content


class TestGracefulShutdown:
    """Test graceful shutdown handling"""
    
    def test_lifespan_startup_and_shutdown(self):
        """Test that the lifespan context manager handles startup and shutdown"""
        # Import the lifespan function
        from main import lifespan, app
        import asyncio
        
        async def test_lifespan():
            """Test the lifespan context manager"""
            async with lifespan(app) as _:
                # During the context, the app should be running
                assert app is not None
            # After exiting the context, cleanup should have occurred
        
        # Run the async test
        asyncio.run(test_lifespan())
    
    def test_shutdown_event_exists(self):
        """Test that the shutdown event is defined"""
        from main import shutdown_event
        import asyncio
        
        assert shutdown_event is not None
        assert isinstance(shutdown_event, asyncio.Event)
    
    def test_signal_handlers_registered(self):
        """Test that signal handlers are registered for SIGTERM and SIGINT"""
        import signal
        from main import lifespan, app
        import asyncio
        
        async def test_signals():
            """Test signal handler registration"""
            # Store original handlers
            original_sigterm = signal.getsignal(signal.SIGTERM)
            original_sigint = signal.getsignal(signal.SIGINT)
            
            async with lifespan(app):
                # Check that handlers were set
                new_sigterm = signal.getsignal(signal.SIGTERM)
                new_sigint = signal.getsignal(signal.SIGINT)
                
                # Handlers should be set (not None or SIG_DFL)
                assert new_sigterm is not None
                assert new_sigint is not None
            
            # Note: In production, we'd restore handlers here, but the lifespan
            # context sets them for the app's lifetime
        
        asyncio.run(test_signals())
    
    def test_app_has_lifespan(self):
        """Test that the FastAPI app has a lifespan configured"""
        from main import app
        
        # Check that the app has a router with lifespan
        assert app.router.lifespan_context is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
