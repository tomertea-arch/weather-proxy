"""
Test script to verify logging format includes request IDs
"""
import logging
import sys
from io import StringIO
from contextvars import ContextVar


# Request ID context variable
request_id_context: ContextVar[str] = ContextVar('request_id', default='no-request-id')


class RequestIDFilter(logging.Filter):
    """Logging filter to inject request_id into all log records"""
    
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True


def test_logging_format():
    """Test that logging format includes request ID"""
    # Create a string buffer to capture log output
    log_stream = StringIO()
    
    # Setup logger
    test_logger = logging.getLogger("test_logger")
    test_logger.setLevel(logging.INFO)
    test_logger.handlers.clear()
    
    # Create formatter with request_id
    formatter = logging.Formatter('[%(request_id)s] - %(levelname)s - %(message)s')
    
    # Create handler
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())
    
    # Add handler to logger
    test_logger.addHandler(handler)
    test_logger.propagate = False
    
    # Test 1: Log without request ID (should show default)
    test_logger.info("Test message without request ID")
    output1 = log_stream.getvalue()
    print("Test 1 - Without request ID:")
    print(f"  Output: {output1.strip()}")
    assert "[no-request-id]" in output1, "Should show default request ID"
    assert "Test message without request ID" in output1
    
    # Test 2: Log with request ID set
    log_stream.truncate(0)
    log_stream.seek(0)
    request_id_context.set("abc-123-def-456")
    test_logger.info("Test message with request ID")
    output2 = log_stream.getvalue()
    print("\nTest 2 - With request ID:")
    print(f"  Output: {output2.strip()}")
    assert "[abc-123-def-456]" in output2, "Should show custom request ID"
    assert "Test message with request ID" in output2
    
    # Test 3: Log with different request ID
    log_stream.truncate(0)
    log_stream.seek(0)
    request_id_context.set("xyz-789-uvw-012")
    test_logger.info("Another test message")
    output3 = log_stream.getvalue()
    print("\nTest 3 - With different request ID:")
    print(f"  Output: {output3.strip()}")
    assert "[xyz-789-uvw-012]" in output3, "Should show updated request ID"
    assert "Another test message" in output3
    
    print("\n✅ All logging format tests passed!")


if __name__ == "__main__":
    test_logging_format()
