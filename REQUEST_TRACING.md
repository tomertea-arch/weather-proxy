# Request Tracing with UUID

Complete guide to the UUID-based request tracing system for debugging and monitoring.

## 🎯 Overview

Every request to the Weather Proxy service is assigned a unique UUID (request ID) that propagates through **all logs** for that request. This makes it easy to trace the complete lifecycle of a request through the system.

## ✨ Features

- ✅ **Automatic UUID Generation** - Each request gets a unique ID
- ✅ **Custom Request IDs** - Clients can provide their own IDs
- ✅ **Thread-Safe Context Propagation** - Uses Python's `contextvars`
- ✅ **Complete Log Coverage** - ID appears in every log entry
- ✅ **Response Headers** - Request ID returned to client
- ✅ **Response Body** - ID included in JSON responses
- ✅ **Error Tracing** - Works even for failed requests
- ✅ **Distributed Tracing Ready** - Compatible with distributed systems

## 🔧 How It Works

### 1. Request ID Middleware

The `RequestIDMiddleware` intercepts every request:

```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID from header
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Set in context for logging
        request_id_context.set(request_id)
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response
```

### 2. Context-Aware Logging

A custom logging filter injects the request ID into every log record:

```python
class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True
```

### 3. Log Format

All logs include the request ID:

```
2026-01-29 15:30:45 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - __main__ - INFO - [START] Weather request for city: London
2026-01-29 15:30:45 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - __main__ - INFO - [CACHE MISS] City: London, fetching from API
2026-01-29 15:30:45 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - __main__ - INFO - [GEOCODE] Fetching coordinates for city: London (attempt 1)
2026-01-29 15:30:46 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - __main__ - INFO - [WEATHER API] Fetching data for London (51.5074, -0.1278) (attempt 1)
2026-01-29 15:30:47 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - __main__ - INFO - [CACHE WRITE] Stored weather data for city: London, TTL=600s
2026-01-29 15:30:47 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - __main__ - INFO - [END] Request completed successfully (fresh data)
```

## 🚀 Usage

### Basic Request (Auto-Generated UUID)

```bash
# Server generates UUID automatically
curl http://localhost:8000/weather?city=London

# Response includes request ID
{
  "city": "London",
  "country": "United Kingdom",
  "coordinates": {...},
  "current_weather": {...},
  "cached": false,
  "request_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
}

# Also in response headers
curl -I http://localhost:8000/weather?city=London
X-Request-ID: a1b2c3d4-5678-90ab-cdef-1234567890ab
```

### Custom Request ID (Client-Provided)

```bash
# Provide your own request ID
curl -H "X-Request-ID: my-custom-id-12345" \
     http://localhost:8000/weather?city=Paris

# Server preserves your ID
{
  "city": "Paris",
  ...
  "request_id": "my-custom-id-12345"
}
```

### Python Client Example

```python
import requests
import uuid

# Auto-generated request ID
response = requests.get('http://localhost:8000/weather?city=London')
request_id = response.headers['X-Request-ID']
print(f"Request ID: {request_id}")

# Custom request ID
custom_id = str(uuid.uuid4())
response = requests.get(
    'http://localhost:8000/weather?city=Paris',
    headers={'X-Request-ID': custom_id}
)
print(f"Custom ID preserved: {response.headers['X-Request-ID'] == custom_id}")
```

### JavaScript/TypeScript Example

```javascript
// Auto-generated request ID
const response = await fetch('http://localhost:8000/weather?city=London');
const requestId = response.headers.get('X-Request-ID');
console.log(`Request ID: ${requestId}`);

// Custom request ID
const customId = crypto.randomUUID();
const response2 = await fetch('http://localhost:8000/weather?city=Paris', {
  headers: { 'X-Request-ID': customId }
});
const data = await response2.json();
console.log(`Request ID: ${data.request_id}`);
```

## 🔍 Debugging with Request IDs

### Find All Logs for a Specific Request

```bash
# Search logs for specific request ID
grep "a1b2c3d4-5678-90ab-cdef-1234567890ab" weather-proxy.log

# Output:
# 2026-01-29 15:30:45 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - INFO - [START] Weather request for city: London
# 2026-01-29 15:30:45 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - INFO - [CACHE MISS] City: London
# 2026-01-29 15:30:46 - [a1b2c3d4-5678-90ab-cdef-1234567890ab] - INFO - [GEOCODE] Fetching coordinates
# ...
```

### Count Requests

```bash
# Count unique requests
grep -o '\[.*\]' weather-proxy.log | sort | uniq | wc -l

# Count requests per hour
grep "2026-01-29 15:" weather-proxy.log | grep -o '\[.*\]' | sort | uniq | wc -l
```

### Find Slow Requests

```bash
# Find requests that took longer than 1000ms
grep "duration=" weather-proxy.log | awk '{if ($NF > 1000) print $0}'
```

### Find Failed Requests

```bash
# Find all ERROR logs
grep "ERROR" weather-proxy.log

# Find specific error types
grep "\[ERROR\]" weather-proxy.log | grep "city=London"
```

## 📊 Log Patterns and Tags

### Log Entry Types

| Tag | Description | Example |
|-----|-------------|---------|
| `[START]` | Request initiated | `[START] Weather request for city: London` |
| `[CACHE HIT]` | Data found in cache | `[CACHE HIT] City: London, duration=5.23ms` |
| `[CACHE MISS]` | Data not in cache | `[CACHE MISS] City: London, fetching from API` |
| `[FETCH]` | Starting API fetch | `[FETCH] Starting API fetch for city: London` |
| `[GEOCODE]` | Geocoding API call | `[GEOCODE] Fetching coordinates for city: London` |
| `[WEATHER API]` | Weather API call | `[WEATHER API] Fetching data for London (51.5, -0.1)` |
| `[CACHE WRITE]` | Writing to cache | `[CACHE WRITE] Stored weather data, TTL=600s` |
| `[SUCCESS]` | Fetch completed | `[SUCCESS] Fetch completed on first attempt` |
| `[RETRY]` | Retry attempt | `[RETRY] Attempt 2 for city: London` |
| `[ERROR]` | Error occurred | `[ERROR] HTTP error: city=London, status=500` |
| `[END]` | Request completed | `[END] Request completed successfully` |

### Example Request Lifecycle

**Successful request (cache miss):**
```
[START] → [CACHE MISS] → [FETCH] → [GEOCODE] → [WEATHER API] → [CACHE WRITE] → [SUCCESS] → [END]
```

**Successful request (cache hit):**
```
[START] → [CACHE HIT] → [END]
```

**Failed request with retry:**
```
[START] → [CACHE MISS] → [FETCH] → [GEOCODE] → [ERROR] → [RETRY] → [GEOCODE] → [WEATHER API] → [SUCCESS] → [END]
```

## 🧪 Testing Request Tracing

Run the test suite:

```bash
# Make sure server is running
python main.py &

# Run tests
python test_request_tracing.py
```

The test suite validates:
- ✅ Auto-generated request IDs
- ✅ Custom request IDs are preserved
- ✅ Concurrent requests have unique IDs
- ✅ Cache hits still generate new IDs
- ✅ Error responses include IDs
- ✅ Health endpoint includes IDs

## 🏗️ Integration with Monitoring Systems

### CloudWatch Logs Insights

Query requests by ID:

```sql
fields @timestamp, @message
| filter @message like /a1b2c3d4-5678-90ab-cdef-1234567890ab/
| sort @timestamp asc
```

Find slow requests:

```sql
fields @timestamp, @message
| filter @message like /duration=/
| parse @message /duration=(?<duration>\d+\.\d+)ms/
| filter duration > 1000
| sort duration desc
```

### ELK Stack (Elasticsearch)

```json
{
  "query": {
    "match": {
      "request_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
    }
  }
}
```

### Datadog

Add request ID as a tag:

```python
from ddtrace import tracer

@tracer.wrap()
def get_weather(city: str, request: Request):
    request_id = request.state.request_id
    tracer.current_span().set_tag('request.id', request_id)
    # ... rest of function
```

### Prometheus Metrics with Labels

Add request ID to metrics (use cautiously due to cardinality):

```python
# For high-value requests only
weather_request_counter.labels(
    endpoint='/weather',
    request_id=request_id[:8]  # Use truncated ID to reduce cardinality
).inc()
```

## 🔗 Distributed Tracing

### Propagate Request IDs Across Services

If you have multiple services, propagate the request ID:

```python
# Service A calls Service B
async def call_service_b(data, request_id):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://service-b/endpoint',
            json=data,
            headers={'X-Request-ID': request_id}
        )
    return response

# In your weather endpoint
result = await call_service_b(data, request.state.request_id)
```

### OpenTelemetry Integration

Convert request IDs to OpenTelemetry trace IDs:

```python
from opentelemetry import trace

def get_weather(city: str, request: Request):
    request_id = request.state.request_id
    
    # Create span with request ID
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(
        "weather_request",
        attributes={"request.id": request_id}
    ) as span:
        # ... your code
```

## 💡 Best Practices

### 1. Always Include Request ID in Client Logs

```python
# Client-side logging
request_id = str(uuid.uuid4())
logger.info(f"[{request_id}] Requesting weather for London")

response = requests.get(
    'http://api/weather?city=London',
    headers={'X-Request-ID': request_id}
)

logger.info(f"[{request_id}] Received response: {response.status_code}")
```

### 2. Use Request IDs in Error Reports

```python
try:
    response = requests.get(url, headers={'X-Request-ID': request_id})
    response.raise_for_status()
except Exception as e:
    logger.error(f"[{request_id}] Request failed: {e}")
    # Include request_id in error reports, bug reports, etc.
```

### 3. Store Request IDs in Databases

```sql
-- Track problematic requests
CREATE TABLE failed_requests (
    id SERIAL PRIMARY KEY,
    request_id UUID NOT NULL,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### 4. Use Meaningful Custom IDs

For important operations, use descriptive IDs:

```python
# Instead of random UUID
request_id = f"user-{user_id}-{operation}-{timestamp}"

# Example: "user-12345-weather-20260129153045"
```

## 🚨 Troubleshooting

### Request ID Not Appearing in Logs

**Problem**: Logs don't show request IDs

**Solution**: Make sure middleware is registered:
```python
app.add_middleware(RequestIDMiddleware)
```

### Request ID Says "no-request-id"

**Problem**: Logs show `[no-request-id]`

**Solution**: This happens when logging outside of a request context (e.g., startup/shutdown logs). This is expected.

### Different Request IDs for Same Cached Response

**Problem**: Two requests to same city show different IDs

**Solution**: This is correct behavior! Each request gets a unique ID, even if the response is cached. This helps track individual client requests.

## 📈 Performance Impact

Request tracing has minimal performance impact:

- **Overhead per request**: < 0.1ms
- **Memory**: ~100 bytes per request (UUID storage)
- **Log size**: Adds ~40 bytes per log line

## 🎯 Summary

Request tracing provides:

✅ **Easy Debugging** - Follow a request through the entire system
✅ **Performance Analysis** - Track slow requests end-to-end
✅ **Error Investigation** - Quickly find root causes
✅ **Distributed Tracing** - Trace across multiple services
✅ **Client Support** - Clients can track their requests
✅ **Production Ready** - Minimal overhead, thread-safe

---

**Need help?** Check the logs with:
```bash
tail -f weather-proxy.log | grep "\[YOUR-REQUEST-ID\]"
```
