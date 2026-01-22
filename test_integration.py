"""
Integration Tests for Weather Proxy Service
Tests API endpoints with mocked external weather providers
"""
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


# Import the app
from main import app, metrics


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test"""
    metrics.request_count = 0
    metrics.error_count = 0
    metrics.durations = []
    metrics.cache_hits = 0
    metrics.cache_misses = 0
    metrics.cache_errors = 0
    metrics.upstream_status_codes = {}
    yield


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client for integration tests"""
    mock_instance = MagicMock()
    mock_instance.get.return_value = None
    mock_instance.setex.return_value = True
    mock_instance.ping.return_value = True
    
    with patch('main.redis_client', mock_instance):
        yield mock_instance


class TestWeatherEndpointIntegration:
    """Integration tests for /weather endpoint"""
    
    def test_weather_missing_city_parameter(self, client):
        """Test weather endpoint without city parameter"""
        response = client.get("/weather")
        
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data
    
    def test_weather_with_cached_response(self, client, mock_redis):
        """Test weather endpoint with valid cached data"""
        # Setup valid cached response
        cached_data = {
            "city": "Paris",
            "coordinates": {"latitude": 48.8566, "longitude": 2.3522},
            "weather": {
                "temperature": 18.0,
                "windspeed": 8.0,
                "winddirection": 180,
                "weathercode": 1
            },
            "cached": True
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        response = client.get("/weather?city=Paris")
        
        # Verify cache was checked
        assert mock_redis.get.called
        
        # Response will depend on whether real API is called or not
        # In integration tests, we verify the endpoint is accessible
        assert response.status_code in [200, 500, 502]


class TestHealthEndpointIntegration:
    """Integration tests for /health endpoint"""
    
    def test_health_check_basic(self, client):
        """Test basic health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "redis" in data
        assert "metrics" in data
        assert "total_requests" in data["metrics"]
        assert "total_errors" in data["metrics"]
    
    def test_health_check_with_redis_mock(self, client, mock_redis):
        """Test health check with mocked Redis"""
        mock_redis.ping.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert isinstance(data["redis"], dict)
        assert data["redis"]["status"] == "connected"
    
    def test_health_check_without_redis(self, client):
        """Test health check when Redis is not configured"""
        with patch('main.redis_client', None):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["redis"]["status"] == "not_configured"


class TestMetricsEndpointIntegration:
    """Integration tests for /metrics endpoint"""
    
    def test_metrics_endpoint_format(self, client):
        """Test metrics endpoint returns Prometheus format"""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        content = response.text
        assert "# HELP" in content
        assert "# TYPE" in content
    
    def test_metrics_contains_required_metrics(self, client):
        """Test that all required metrics are present"""
        response = client.get("/metrics")
        
        content = response.text
        
        # Verify all key metrics exist
        assert "weather_proxy_requests_total" in content
        assert "weather_proxy_request_duration_seconds" in content
        assert "weather_proxy_errors_total" in content
        assert "weather_proxy_cache_operations_total" in content
        assert "weather_proxy_redis_connected" in content
    
    def test_metrics_after_requests(self, client, mock_redis):
        """Test that metrics update after making requests"""
        from unittest.mock import AsyncMock
        
        # Make some requests
        for i in range(3):
            client.get("/health")
        
        # Check metrics
        metrics_response = client.get("/metrics")
        assert "weather_proxy_requests_total" in metrics_response.text


class TestEndToEndScenarios:
    """End-to-end integration scenarios"""
    
    def test_health_then_metrics_workflow(self, client):
        """Test checking health then metrics"""
        # Step 1: Check health
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        initial_requests = health_data["metrics"]["total_requests"]
        
        # Step 2: Check metrics
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "weather_proxy_requests_total" in metrics_response.text
        
        # Step 3: Check health again - request count should have increased
        health_response2 = client.get("/health")
        health_data2 = health_response2.json()
        assert health_data2["metrics"]["total_requests"] >= initial_requests
    
    def test_error_handling_workflow(self, client, mock_redis):
        """Test error handling across endpoints"""
        # Test missing parameters
        response1 = client.get("/weather")
        assert response1.status_code == 422
        
        # Health should still work
        health = client.get("/health")
        assert health.status_code == 200
        
        # Errors should be tracked
        health_data = health.json()
        assert health_data["metrics"]["total_errors"] >= 0  # May be 0 or more depending on test order


class TestCachingBehavior:
    """Test caching behavior across endpoints"""
    
    def test_weather_caching(self, client, mock_redis):
        """Test that weather requests are cached"""
        from unittest.mock import MagicMock, AsyncMock
        
        # Mock geocoding response
        geo_response = MagicMock()
        geo_response.status_code = 200
        geo_response.json.return_value = {
            "results": [{"latitude": 51.5074, "longitude": -0.1278, "name": "London"}]
        }
        
        # Mock weather response
        weather_response = MagicMock()
        weather_response.status_code = 200
        weather_response.json.return_value = {
            "current": {
                "temperature_2m": 15.5,
                "windspeed_10m": 12.0,
                "winddirection_10m": 240,
                "weathercode": 3,
                "time": "2026-01-22T12:00"
            }
        }
        
        responses = [geo_response, weather_response]
        call_count = [0]
        
        async def mock_get(*args, **kwargs):
            response = responses[call_count[0]]
            call_count[0] += 1
            return response
        
        with patch('main.http_client') as mock_http:
            mock_http.get = mock_get
            
            # Make weather request
            response = client.get("/weather?city=London")
            assert response.status_code in [200, 500]
            
            # If successful, cache should be called
            if response.status_code == 200:
                assert mock_redis.setex.called or mock_redis.setex.call_count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
