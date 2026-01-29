#!/usr/bin/env python3
"""
Test script to demonstrate UUID-based request tracing functionality.
Shows how request IDs propagate through all logs for debugging.
"""

import requests
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://localhost:8000"
TEST_CITIES = ["London", "Paris", "Tokyo", "New York", "Sydney"]


def test_basic_request_tracing():
    """Test basic request tracing - server generates UUID"""
    print("=" * 80)
    print("TEST 1: Basic Request Tracing (Server-Generated UUID)")
    print("=" * 80)
    
    city = "London"
    response = requests.get(f"{BASE_URL}/weather", params={"city": city})
    
    # Check response
    print(f"\n✓ Request to: {city}")
    print(f"✓ Status Code: {response.status_code}")
    
    # Get request ID from response header
    request_id = response.headers.get('X-Request-ID')
    print(f"✓ Request ID from header: {request_id}")
    
    # Check if request ID is in response body
    data = response.json()
    if 'request_id' in data:
        print(f"✓ Request ID in response body: {data['request_id']}")
        assert data['request_id'] == request_id, "Request ID mismatch!"
    
    print(f"✓ City: {data['city']}")
    print(f"✓ Cached: {data.get('cached', 'N/A')}")
    print(f"\n✅ PASSED: Request ID successfully propagated through response\n")
    
    return request_id


def test_custom_request_id():
    """Test with custom request ID in header"""
    print("=" * 80)
    print("TEST 2: Custom Request ID (Client-Provided UUID)")
    print("=" * 80)
    
    # Generate custom request ID
    custom_request_id = str(uuid.uuid4())
    print(f"\n✓ Custom Request ID: {custom_request_id}")
    
    city = "Paris"
    headers = {"X-Request-ID": custom_request_id}
    response = requests.get(
        f"{BASE_URL}/weather",
        params={"city": city},
        headers=headers
    )
    
    # Verify request ID matches
    returned_request_id = response.headers.get('X-Request-ID')
    print(f"✓ Returned Request ID: {returned_request_id}")
    
    assert custom_request_id == returned_request_id, "Custom request ID not preserved!"
    
    data = response.json()
    print(f"✓ Request ID in response body: {data.get('request_id', 'N/A')}")
    print(f"✓ City: {data['city']}")
    
    print(f"\n✅ PASSED: Custom request ID successfully preserved\n")
    
    return custom_request_id


def test_concurrent_requests():
    """Test multiple concurrent requests - each should have unique request ID"""
    print("=" * 80)
    print("TEST 3: Concurrent Requests (Unique Request IDs)")
    print("=" * 80)
    
    print(f"\n✓ Sending {len(TEST_CITIES)} concurrent requests...")
    
    request_ids = []
    
    def fetch_weather(city):
        response = requests.get(f"{BASE_URL}/weather", params={"city": city})
        request_id = response.headers.get('X-Request-ID')
        data = response.json()
        return {
            'city': city,
            'request_id': request_id,
            'cached': data.get('cached', False),
            'status': response.status_code
        }
    
    # Execute concurrent requests
    with ThreadPoolExecutor(max_workers=len(TEST_CITIES)) as executor:
        futures = [executor.submit(fetch_weather, city) for city in TEST_CITIES]
        
        for future in as_completed(futures):
            result = future.result()
            print(f"  • {result['city']:<15} | Request ID: {result['request_id']} | "
                  f"Cached: {result['cached']} | Status: {result['status']}")
            request_ids.append(result['request_id'])
    
    # Verify all request IDs are unique
    unique_ids = set(request_ids)
    print(f"\n✓ Total requests: {len(request_ids)}")
    print(f"✓ Unique request IDs: {len(unique_ids)}")
    
    assert len(request_ids) == len(unique_ids), "Request IDs are not unique!"
    
    print(f"\n✅ PASSED: All concurrent requests have unique request IDs\n")
    
    return request_ids


def test_cache_behavior_with_tracing():
    """Test that request IDs work correctly with cached responses"""
    print("=" * 80)
    print("TEST 4: Cache Behavior with Request Tracing")
    print("=" * 80)
    
    city = "Berlin"
    
    # First request (will cache)
    print(f"\n✓ First request (should be cached): {city}")
    response1 = requests.get(f"{BASE_URL}/weather", params={"city": city})
    data1 = response1.json()
    request_id_1 = response1.headers.get('X-Request-ID')
    
    print(f"  • Request ID: {request_id_1}")
    print(f"  • Cached: {data1.get('cached', False)}")
    print(f"  • City: {data1['city']}")
    
    time.sleep(1)  # Small delay
    
    # Second request (should hit cache with NEW request ID)
    print(f"\n✓ Second request (should hit cache): {city}")
    response2 = requests.get(f"{BASE_URL}/weather", params={"city": city})
    data2 = response2.json()
    request_id_2 = response2.headers.get('X-Request-ID')
    
    print(f"  • Request ID: {request_id_2}")
    print(f"  • Cached: {data2.get('cached', False)}")
    print(f"  • City: {data2['city']}")
    
    # Verify request IDs are different
    assert request_id_1 != request_id_2, "Request IDs should be different for each request!"
    
    print(f"\n✓ Different request IDs confirmed")
    print(f"  • First:  {request_id_1}")
    print(f"  • Second: {request_id_2}")
    
    print(f"\n✅ PASSED: Each request gets unique ID even with cached responses\n")


def test_error_scenarios_with_tracing():
    """Test that request IDs work correctly with error responses"""
    print("=" * 80)
    print("TEST 5: Error Scenarios with Request Tracing")
    print("=" * 80)
    
    # Test 1: Missing city parameter
    print("\n✓ Test: Missing city parameter (400 error)")
    response = requests.get(f"{BASE_URL}/weather")
    request_id = response.headers.get('X-Request-ID')
    print(f"  • Request ID: {request_id}")
    print(f"  • Status: {response.status_code}")
    print(f"  • Error: {response.json()['detail']}")
    assert response.status_code == 400
    assert request_id is not None, "Request ID should be present even on errors!"
    
    # Test 2: Invalid city (404 error)
    print("\n✓ Test: Invalid city (404 error)")
    response = requests.get(f"{BASE_URL}/weather", params={"city": "InvalidCity12345XYZ"})
    request_id = response.headers.get('X-Request-ID')
    print(f"  • Request ID: {request_id}")
    print(f"  • Status: {response.status_code}")
    if response.status_code == 404:
        print(f"  • Error: {response.json()['detail']}")
    assert request_id is not None, "Request ID should be present even on errors!"
    
    print(f"\n✅ PASSED: Request IDs present even for error responses\n")


def test_health_endpoint():
    """Test health endpoint (should also have request ID)"""
    print("=" * 80)
    print("TEST 6: Health Endpoint Request Tracing")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/health")
    request_id = response.headers.get('X-Request-ID')
    
    print(f"\n✓ Health check status: {response.status_code}")
    print(f"✓ Request ID: {request_id}")
    
    data = response.json()
    print(f"✓ Service status: {data['status']}")
    
    assert request_id is not None, "Health endpoint should also have request ID!"
    
    print(f"\n✅ PASSED: Health endpoint includes request ID\n")


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "UUID REQUEST TRACING TEST SUITE" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    try:
        # Run tests
        test_basic_request_tracing()
        test_custom_request_id()
        test_concurrent_requests()
        test_cache_behavior_with_tracing()
        test_error_scenarios_with_tracing()
        test_health_endpoint()
        
        # Summary
        print("=" * 80)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 80)
        print()
        print("✅ Request ID generation works correctly")
        print("✅ Request ID propagates through all responses")
        print("✅ Custom request IDs are preserved")
        print("✅ Concurrent requests have unique IDs")
        print("✅ Cache hits still generate new request IDs")
        print("✅ Error responses include request IDs")
        print()
        print("📝 To trace a specific request in logs, search for:")
        print("   grep '[request-id]' weather-proxy.log")
        print()
        print("💡 Tips:")
        print("   • Check server logs to see request IDs in action")
        print("   • Use X-Request-ID header to provide custom IDs")
        print("   • All logs for a request will have the same ID")
        print("   • Great for debugging distributed systems!")
        print()
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return 1
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERROR: Cannot connect to {BASE_URL}")
        print("   Make sure the server is running: python main.py\n")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
