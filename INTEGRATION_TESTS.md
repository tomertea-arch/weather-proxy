# Integration Tests Documentation

## Overview
Comprehensive integration tests for the Weather Proxy microservice that verify API endpoints with mocked external weather providers and dependencies.

## Test File
`test_integration.py` - 19 integration tests covering real-world scenarios

## Test Results
**✅ 19/19 tests passing (100%)**

```bash
pytest test_integration.py -v
```

## Test Organization

### 1. TestWeatherEndpointIntegration (2 tests)
Tests the `/weather` endpoint with various scenarios:

#### `test_weather_missing_city_parameter`
- **Purpose**: Validates parameter validation
- **Test**: Request without city parameter
- **Expected**: 422 Validation Error
- **Verifies**: FastAPI parameter validation works correctly

#### `test_weather_with_cached_response`
- **Purpose**: Tests caching behavior for weather requests
- **Test**: Sets up cached data in Redis mock and requests weather
- **Expected**: Cache is checked, endpoint returns valid response
- **Verifies**: Redis cache integration works

### 2. TestProxyEndpointIntegration (4 tests)
Tests the `/proxy` endpoint with different HTTP methods and scenarios:

#### `test_proxy_missing_url_parameter`
- **Purpose**: Validates required URL parameter
- **Test**: Request without url parameter
- **Expected**: 400 Bad Request
- **Verifies**: Parameter validation for proxy endpoint

#### `test_proxy_with_url_parameter`
- **Purpose**: Tests successful proxy request
- **Test**: GET request with mocked HTTP client
- **Expected**: 200 OK, external API is called
- **Verifies**: Proxy functionality with external API mocking

#### `test_proxy_post_request`
- **Purpose**: Tests POST request proxying
- **Test**: POST request with JSON body
- **Expected**: 201 Created, POST requests not cached
- **Verifies**: POST method support and no caching for non-GET

#### `test_proxy_with_cached_response`
- **Purpose**: Tests cache hit scenario
- **Test**: Sets up cached response, makes GET request
- **Expected**: 200 OK, returns cached data
- **Verifies**: Cache retrieval works correctly

### 3. TestHealthEndpointIntegration (3 tests)
Tests the `/health` endpoint in different Redis configurations:

#### `test_health_check_basic`
- **Purpose**: Basic health check functionality
- **Test**: GET /health
- **Expected**: 200 OK with status, redis, metrics
- **Verifies**: Health endpoint structure and data

#### `test_health_check_with_redis_mock`
- **Purpose**: Health with Redis connected
- **Test**: Mock Redis as connected, check health
- **Expected**: redis.status = "connected"
- **Verifies**: Redis status reporting when connected

#### `test_health_check_without_redis`
- **Purpose**: Health without Redis
- **Test**: Set redis_client to None
- **Expected**: redis.status = "not_configured"
- **Verifies**: Graceful handling of missing Redis

### 4. TestMetricsEndpointIntegration (3 tests)
Tests the `/metrics` Prometheus endpoint:

#### `test_metrics_endpoint_format`
- **Purpose**: Validates Prometheus format
- **Test**: GET /metrics
- **Expected**: text/plain content-type, # HELP, # TYPE
- **Verifies**: Prometheus format compliance

#### `test_metrics_contains_required_metrics`
- **Purpose**: Checks all required metrics exist
- **Test**: Parse metrics output
- **Expected**: All key metrics present (requests, duration, errors, cache, redis)
- **Verifies**: Complete metrics exposure

#### `test_metrics_after_requests`
- **Purpose**: Metrics update after activity
- **Test**: Make requests, check metrics
- **Expected**: Metrics increment correctly
- **Verifies**: Real-time metrics tracking

### 5. TestEndToEndScenarios (4 tests)
End-to-end workflows testing multiple endpoints together:

#### `test_health_then_metrics_workflow`
- **Purpose**: Sequential endpoint access
- **Test**: health → metrics → health
- **Expected**: Request counts increase
- **Verifies**: Metrics tracking across multiple requests

#### `test_multiple_proxy_requests`
- **Purpose**: Multiple proxy calls
- **Test**: 3 different URLs through proxy
- **Expected**: All succeed, HTTP client called multiple times
- **Verifies**: Proxy handles concurrent different requests

#### `test_error_handling_workflow`
- **Purpose**: Error scenarios across endpoints
- **Test**: Invalid requests to weather and proxy, then health check
- **Expected**: Errors tracked in metrics
- **Verifies**: Error tracking and health endpoint reliability

#### `test_proxy_different_http_methods`
- **Purpose**: HTTP method support
- **Test**: GET, POST, PUT requests
- **Expected**: All methods work
- **Verifies**: Full HTTP method support in proxy

### 6. TestCachingBehavior (3 tests)
Detailed caching mechanism tests:

#### `test_proxy_caches_get_requests`
- **Purpose**: GET requests are cached
- **Test**: Make GET request, check Redis
- **Expected**: redis.setex() called
- **Verifies**: Cache writes for GET requests

#### `test_proxy_does_not_cache_post_requests`
- **Purpose**: POST requests bypass cache
- **Test**: Make POST request, check Redis
- **Expected**: redis.setex() NOT called
- **Verifies**: POST requests not cached

#### `test_cache_hit_metrics`
- **Purpose**: Cache hits tracked in metrics
- **Test**: Setup cache hit, check /metrics
- **Expected**: cache_operations_total increments
- **Verifies**: Cache metrics tracking

## Mocking Strategy

### Redis Mocking
```python
@pytest.fixture
def mock_redis():
    """Mock Redis client for integration tests"""
    mock_instance = MagicMock()
    mock_instance.get.return_value = None
    mock_instance.setex.return_value = True
    mock_instance.ping.return_value = True
    
    with patch('main.redis_client', mock_instance):
        yield mock_instance
```

**Why**: Isolates tests from real Redis dependency, allows control over cache behavior

### HTTP Client Mocking
```python
async def mock_request(*args, **kwargs):
    return mock_response

with patch('main.http_client') as mock_http:
    mock_http.request = mock_request
```

**Why**: Prevents real external API calls, enables testing error scenarios

### Metrics Reset
```python
@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset metrics before each test"""
    metrics.request_count = 0
    # ... reset all metrics
    yield
```

**Why**: Ensures test isolation, prevents test interdependencies

## Key Integration Points Tested

### 1. External API Integration
- ✅ HTTP client interaction
- ✅ Request/response handling
- ✅ Error propagation from external services

### 2. Redis Caching Integration
- ✅ Cache reads (get)
- ✅ Cache writes (setex)
- ✅ Cache miss handling
- ✅ Graceful degradation without Redis

### 3. Metrics Integration
- ✅ Request counting
- ✅ Error tracking
- ✅ Duration recording
- ✅ Prometheus format export

### 4. FastAPI Integration
- ✅ Parameter validation
- ✅ Request body parsing
- ✅ Response formatting
- ✅ HTTP method routing

## Running Integration Tests

### Run All Integration Tests
```bash
pytest test_integration.py -v
```

### Run Specific Test Class
```bash
pytest test_integration.py::TestProxyEndpointIntegration -v
```

### Run Specific Test
```bash
pytest test_integration.py::TestMetricsEndpointIntegration::test_metrics_endpoint_format -v
```

### Run with Coverage
```bash
pytest test_integration.py --cov=main --cov-report=html
```

## Test Patterns Used

### 1. Arrange-Act-Assert (AAA)
```python
def test_example(self, client, mock_redis):
    # Arrange: Setup mocks and data
    mock_redis.get.return_value = json.dumps(data)
    
    # Act: Make the request
    response = client.get("/endpoint")
    
    # Assert: Verify results
    assert response.status_code == 200
```

### 2. Fixture-Based Setup
- Reusable test fixtures for client, mocks
- Auto-reset fixtures for isolation
- Parameterized fixtures for variations

### 3. Mock Verification
- Verify mock methods were called
- Check call counts and arguments
- Validate side effects

## Differences from Unit Tests

| Aspect | Unit Tests | Integration Tests |
|--------|-----------|-------------------|
| **Scope** | Single function/class | Multiple components |
| **Dependencies** | All mocked | Some real, some mocked |
| **Speed** | Very fast (<1s) | Fast (~0.5s) |
| **Purpose** | Code correctness | Component interaction |
| **External APIs** | Always mocked | Mocked for testing |
| **Database** | Always mocked | Mocked but tested integration |
| **Coverage** | Code paths | User workflows |

## Benefits of Integration Tests

### 1. Real-World Scenarios
- Tests actual user workflows
- Validates API contracts
- Catches integration bugs

### 2. Mocked External Dependencies
- No real API calls
- Deterministic test results
- Fast execution

### 3. End-to-End Confidence
- Multiple endpoints work together
- Caching behaves correctly
- Metrics track accurately

### 4. Regression Prevention
- Detects breaking changes
- Validates refactoring
- Documents expected behavior

## Common Issues and Solutions

### Issue: Async Mocking Complexity
**Problem**: AsyncMock doesn't always work with FastAPI TestClient

**Solution**: Use sync functions that return mock objects
```python
async def mock_request(*args, **kwargs):
    return mock_response  # Return sync mock
```

### Issue: Redis Mock Not Applied
**Problem**: Mock doesn't replace actual redis_client

**Solution**: Use `with patch('main.redis_client', mock_instance)`

### Issue: Test Interdependence
**Problem**: Tests affect each other's metrics

**Solution**: autouse fixture to reset metrics before each test

## Future Enhancements

### Potential Additions
- [ ] Test retry mechanism with transient failures
- [ ] Test circuit breaker behavior
- [ ] Test concurrent request handling
- [ ] Test rate limiting (if added)
- [ ] Test authentication/authorization (if added)
- [ ] Performance/load testing scenarios

### Potential Improvements
- [ ] Parameterized tests for similar scenarios
- [ ] Snapshot testing for complex responses
- [ ] Contract testing with real API schemas
- [ ] Database integration tests (if database added)

## Best Practices Demonstrated

1. **Test Isolation**: Each test is independent
2. **Descriptive Names**: Test names explain what they verify
3. **Single Responsibility**: Each test checks one thing
4. **Arrange-Act-Assert**: Clear test structure
5. **Mock Verification**: Confirm expected interactions
6. **Error Cases**: Test both success and failure paths
7. **Documentation**: Docstrings explain test purpose

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Run Integration Tests
  run: |
    pytest test_integration.py -v --cov=main --cov-report=xml
```

### Docker Testing
```bash
docker run --rm weather-proxy:latest pytest test_integration.py -v
```

### Pre-commit Hook
```bash
#!/bin/bash
pytest test_integration.py --tb=short
if [ $? -ne 0 ]; then
    echo "Integration tests failed!"
    exit 1
fi
```

---

**Status**: ✅ All 19 integration tests passing  
**Coverage**: API endpoints, caching, metrics, error handling  
**Maintenance**: Keep tests updated with API changes  
**Last Updated**: 2026-01-22
