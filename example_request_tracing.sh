#!/bin/bash

###############################################################################
# Example: Request Tracing with UUID
# Demonstrates how request IDs help with debugging
###############################################################################

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         Request Tracing Example - Weather Proxy              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

BASE_URL="http://localhost:8000"

###############################################################################
# Example 1: Basic request with auto-generated ID
###############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Example 1: Auto-Generated Request ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Making request to /weather?city=London..."
echo ""

response=$(curl -s -i "$BASE_URL/weather?city=London")

# Extract request ID from header
request_id=$(echo "$response" | grep -i "X-Request-ID:" | awk '{print $2}' | tr -d '\r')

echo "✓ Request completed"
echo "✓ Request ID: $request_id"
echo ""
echo "To see all logs for this request, run:"
echo "  grep \"$request_id\" weather-proxy.log"
echo ""

###############################################################################
# Example 2: Custom request ID
###############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Example 2: Custom Request ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Generate custom ID
custom_id="my-debug-request-$(date +%s)"
echo "Using custom ID: $custom_id"
echo ""

response=$(curl -s -i -H "X-Request-ID: $custom_id" "$BASE_URL/weather?city=Paris")

returned_id=$(echo "$response" | grep -i "X-Request-ID:" | awk '{print $2}' | tr -d '\r')

echo "✓ Request completed"
echo "✓ Returned ID: $returned_id"
echo ""

if [ "$custom_id" == "$returned_id" ]; then
    echo "✅ Custom ID preserved!"
else
    echo "❌ Custom ID not preserved"
fi

echo ""
echo "To see logs:"
echo "  grep \"$custom_id\" weather-proxy.log"
echo ""

###############################################################################
# Example 3: Multiple concurrent requests
###############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Example 3: Concurrent Requests (Each gets unique ID)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cities=("London" "Paris" "Tokyo" "New York" "Sydney")

echo "Sending 5 concurrent requests..."
echo ""

for city in "${cities[@]}"; do
    (
        response=$(curl -s -i "$BASE_URL/weather?city=$city")
        request_id=$(echo "$response" | grep -i "X-Request-ID:" | awk '{print $2}' | tr -d '\r')
        echo "  • $city: $request_id"
    ) &
done

# Wait for all background jobs
wait

echo ""
echo "✓ Each request has a unique ID"
echo ""

###############################################################################
# Example 4: Tracing errors
###############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Example 4: Tracing Errors"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

error_id="error-trace-$(date +%s)"
echo "Sending invalid request with ID: $error_id"
echo ""

response=$(curl -s -i -H "X-Request-ID: $error_id" "$BASE_URL/weather")

returned_id=$(echo "$response" | grep -i "X-Request-ID:" | awk '{print $2}' | tr -d '\r')
status=$(echo "$response" | grep "HTTP" | awk '{print $2}')

echo "✓ Status: $status"
echo "✓ Request ID: $returned_id"
echo ""
echo "Even errors have request IDs for debugging!"
echo ""
echo "To see error logs:"
echo "  grep \"$error_id\" weather-proxy.log | grep ERROR"
echo ""

###############################################################################
# Example 5: Real-world debugging scenario
###############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Example 5: Real-World Debugging Scenario"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Scenario: User reports slow response for London weather"
echo ""

# Make request and measure time
debug_id="user-complaint-investigation-$(date +%s)"
echo "Investigation ID: $debug_id"
echo ""

start_time=$(date +%s%3N)
response=$(curl -s -H "X-Request-ID: $debug_id" "$BASE_URL/weather?city=London")
end_time=$(date +%s%3N)

duration=$((end_time - start_time))

echo "✓ Response time: ${duration}ms"
echo ""
echo "📊 Debugging steps:"
echo ""
echo "1. Check all logs for this request:"
echo "   grep \"$debug_id\" weather-proxy.log"
echo ""
echo "2. Find timing information:"
echo "   grep \"$debug_id\" weather-proxy.log | grep \"duration=\""
echo ""
echo "3. Check cache behavior:"
echo "   grep \"$debug_id\" weather-proxy.log | grep \"CACHE\""
echo ""
echo "4. Check API calls:"
echo "   grep \"$debug_id\" weather-proxy.log | grep \"API\""
echo ""
echo "5. Look for errors or retries:"
echo "   grep \"$debug_id\" weather-proxy.log | grep -E \"ERROR|RETRY\""
echo ""

###############################################################################
# Summary
###############################################################################
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Request IDs help you:"
echo "  • Track individual requests through the system"
echo "  • Debug issues by following the request lifecycle"
echo "  • Correlate logs across different components"
echo "  • Investigate performance problems"
echo "  • Trace errors from start to finish"
echo ""
echo "💡 Pro Tips:"
echo "  • Use custom IDs for important operations"
echo "  • Include request IDs in error reports"
echo "  • Store request IDs when users report issues"
echo "  • Use request IDs across microservices"
echo ""
echo "📖 For more information:"
echo "  • See REQUEST_TRACING.md for full documentation"
echo "  • Run test_request_tracing.py for automated tests"
echo ""
