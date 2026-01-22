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


class TestProxyEndpoint:
    """Tests for /proxy endpoint"""
    
    def test_proxy_missing_url_parameter(self, client):
        """Test proxy endpoint without url parameter"""
        response = client.get("/proxy/test")
        assert response.status_code == 400
        assert "url" in response.json()["detail"].lower()
    
    def test_proxy_get_request(self, client, mock_redis):
        """Test proxy GET request"""
        mock_redis.get.return_value = None
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = '{"test": "data"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.raise_for_status = Mock()
        
        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        
        with patch('main.redis_client', mock_redis), \
             patch('main.http_client', mock_http_client):
            response = client.get("/proxy/api?url=https://api.example.com/data")
            assert response.status_code == 200
            data = response.json()
            assert data["status_code"] == 200
            assert "test" in data["content"]
    
    def test_proxy_cached_request(self, client, mock_redis):
        """Test proxy GET request with cached response"""
        cached_response = {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "content": '{"cached": true}'
        }
        mock_redis.get.return_value = json.dumps(cached_response)
        
        with patch('main.redis_client', mock_redis):
            response = client.get("/proxy/api?url=https://api.example.com/data")
            assert response.status_code == 200
            # The cached content is returned as the response body
            # JSONResponse with content=cached_data["content"] returns the string directly
            content = response.text
            assert "cached" in content
            # The content should be a JSON string that can be parsed
            if content.startswith('{') or content.startswith('['):
                parsed = json.loads(content)
                # parsed should be a dict with "cached" key
                if isinstance(parsed, dict):
                    assert parsed.get("cached") is True
                else:
                    # If it's not a dict, just verify "cached" is in the string
                    assert "cached" in str(parsed).lower()
            else:
                # If it's not JSON, just check it contains "cached"
                assert "cached" in content.lower()
    
    def test_proxy_post_request(self, client, mock_redis):
        """Test proxy POST request"""
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_response.text = '{"created": true}'
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        
        mock_http_client = AsyncMock()
        mock_http_client.request.return_value = mock_response
        
        with patch('main.redis_client', mock_redis), \
             patch('main.http_client', mock_http_client):
            response = client.post(
                "/proxy/api?url=https://api.example.com/data",
                json={"key": "value"}
            )
            assert response.status_code == 201
            data = response.json()
            assert data["status_code"] == 201


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
