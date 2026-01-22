# Graceful Shutdown Implementation

## Overview
The Weather Proxy microservice implements comprehensive graceful shutdown handling to ensure reliable operation in containerized environments, particularly AWS Fargate.

## Implementation Details

### 1. Signal Handling
**Location:** `main.py` - lifespan context manager

**Signals Handled:**
- `SIGTERM`: Kubernetes/Fargate/Docker container stop signal
- `SIGINT`: Manual interrupt (Ctrl+C) for local development

**Handler Function:**
```python
def handle_shutdown_signal(signum, frame):
    """Handle SIGTERM and SIGINT signals"""
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
    shutdown_event.set()
```

### 2. Lifespan Management
**Modern Approach:** Uses FastAPI's `lifespan` context manager (replaces deprecated `on_event`)

**Lifecycle:**
1. **Startup Phase:**
   - Registers signal handlers for SIGTERM and SIGINT
   - Logs startup completion
   - Prepares shutdown event

2. **Running Phase:**
   - Application handles requests normally
   - Monitors for shutdown signals

3. **Shutdown Phase:**
   - Receives signal (SIGTERM/SIGINT)
   - Waits 2 seconds for in-flight requests to complete
   - Closes HTTP client connections gracefully
   - Closes Redis connections
   - Logs all shutdown steps

### 3. Uvicorn Configuration
**Docker CMD:** `Dockerfile`
```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", 
     "--timeout-graceful-shutdown", "10", "--timeout-keep-alive", "5"]
```

**Parameters:**
- `--timeout-graceful-shutdown 10`: Allows 10 seconds for graceful shutdown
- `--timeout-keep-alive 5`: Keeps idle connections alive for 5 seconds

### 4. Resource Cleanup
**Resources Managed:**
- ✅ HTTP client connections (httpx.AsyncClient)
- ✅ Redis connections
- ✅ In-flight HTTP requests
- ✅ File handlers (logs)

**Error Handling:**
- All cleanup operations are wrapped in try-except blocks
- Errors during shutdown are logged but don't prevent other cleanup

## Benefits for AWS Fargate

### 1. Zero-Downtime Deployments
- Completes active requests before termination
- No HTTP 502/504 errors during rolling updates
- Smooth traffic handoff to new containers

### 2. Resource Management
- Prevents connection leaks
- Cleans up file descriptors
- Releases Redis connections properly

### 3. Compliance
- Works within Fargate's 30-second stop timeout
- Application shuts down in ~12 seconds:
  - 2s grace period for requests
  - 10s uvicorn graceful shutdown
  - Well within the 30s limit

### 4. Observability
- Logs all shutdown steps
- Easy to debug shutdown issues
- Prometheus metrics preserved until the end

## Testing

### Unit Tests
**Location:** `test_main.py::TestGracefulShutdown`

**Tests Included:**
1. ✅ `test_lifespan_startup_and_shutdown` - Verifies lifespan context manager
2. ✅ `test_shutdown_event_exists` - Checks shutdown event is defined
3. ✅ `test_signal_handlers_registered` - Validates signal handler registration
4. ✅ `test_app_has_lifespan` - Confirms FastAPI app has lifespan configured

**Run Tests:**
```bash
pytest test_main.py::TestGracefulShutdown -v
```

### Manual Testing

#### Local Docker Testing
```bash
# Start container
docker run -d --name weather-proxy-test -p 8000:8000 weather-proxy:latest

# Send SIGTERM
docker kill --signal=SIGTERM weather-proxy-test

# Check logs for graceful shutdown
docker logs weather-proxy-test
```

**Expected Log Output:**
```
INFO - Application starting up...
INFO - Signal handlers registered for SIGTERM and SIGINT
INFO - Application shutting down gracefully...
INFO - Waiting for in-flight requests to complete...
INFO - HTTP client closed successfully
INFO - Redis client closed successfully
INFO - Shutdown complete
```

#### Kubernetes/Fargate Testing
```bash
# Deploy to Fargate
# Then trigger a rolling update or manual pod deletion
kubectl delete pod <pod-name>

# Check logs
kubectl logs <pod-name>
```

## Timeline

### Shutdown Sequence (Typical: ~12 seconds)
```
T+0s:   SIGTERM received
T+0s:   Log: "Received SIGTERM signal, initiating graceful shutdown..."
T+0s:   Set shutdown_event
T+0s:   Stop accepting new requests (handled by uvicorn)
T+0-2s: Process in-flight requests
T+2s:   Log: "Waiting for in-flight requests to complete..."
T+2s:   Close HTTP client
T+2s:   Close Redis client
T+2s:   Log: "Shutdown complete"
T+2-12s: Uvicorn final cleanup (up to 10s timeout)
T+12s:  Container exits
```

### AWS Fargate Stop Behavior
1. **T+0s:** ECS sends SIGTERM to container
2. **T+0-30s:** Container gracefully shuts down (our app: ~12s)
3. **T+30s:** If still running, ECS sends SIGKILL (force kill)

**Our app completes in ~12s, well within the 30s limit! ✅**

## Comparison: Before vs After

### Before (Deprecated @app.on_event)
❌ Used deprecated FastAPI event handlers  
❌ No signal handling  
❌ No grace period for in-flight requests  
❌ Basic resource cleanup only  
❌ Limited logging  

### After (Lifespan Context Manager)
✅ Modern FastAPI lifespan pattern  
✅ SIGTERM/SIGINT signal handling  
✅ 2-second grace period for requests  
✅ Comprehensive resource cleanup  
✅ Detailed logging at each step  
✅ Unit tests for shutdown behavior  
✅ Uvicorn graceful shutdown configured  

## Production Checklist

- [x] Signal handlers registered (SIGTERM, SIGINT)
- [x] Lifespan context manager implemented
- [x] Grace period for in-flight requests (2s)
- [x] HTTP client cleanup
- [x] Redis client cleanup
- [x] Error handling during shutdown
- [x] Comprehensive logging
- [x] Unit tests passing
- [x] Docker CMD includes graceful shutdown flags
- [x] Documentation updated
- [x] Tested locally with docker kill --signal=SIGTERM
- [x] Timeline under 30s (Fargate requirement)

## References

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)
- [AWS Fargate Task Stop Behavior](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-lifecycle.html)
- [Container Lifecycle Hooks](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)

---

**Status:** ✅ Production Ready  
**Last Updated:** 2026-01-22  
**Test Coverage:** 4/4 graceful shutdown tests passing
