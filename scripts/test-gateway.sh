#!/bin/bash
# Test AgentCore Gateway before using in Lambda

GATEWAY_URL="$1"
TOKEN="$2"

if [ -z "$GATEWAY_URL" ] || [ -z "$TOKEN" ]; then
    echo "Usage: ./test-gateway.sh <gateway-url> <token>"
    echo ""
    echo "Example:"
    echo "  TOKEN=\$(curl -X POST \"\$TOKEN_URL\" -H \"Authorization: Basic \$(echo -n \"\$CLIENT_ID:\" | base64)\" -d \"grant_type=client_credentials\" | jq -r '.access_token')"
    echo "  ./test-gateway.sh \"\$GATEWAY_URL\" \"\$TOKEN\""
    exit 1
fi

echo "=========================================="
echo "AGENTCORE GATEWAY TEST"
echo "=========================================="
echo "Gateway: $GATEWAY_URL"
echo ""

# Test 1: List tools
echo "1️⃣  Testing tools/list..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | jq -e '.result' > /dev/null 2>&1; then
        echo "   ✅ tools/list succeeded (HTTP $HTTP_CODE)"
        echo "   Available tools:"
        echo "$BODY" | jq -r '.result.tools[].name' | sed 's/^/      - /'
    else
        echo "   ❌ tools/list returned 200 but invalid response"
        echo "$BODY" | jq .
        exit 1
    fi
else
    echo "   ❌ tools/list failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
    exit 1
fi

echo ""

# Test 2: Call a tool
echo "2️⃣  Testing tools/call (CheckSecurityServices)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "SecurityMCPTools___CheckSecurityServices",
      "arguments": {"region": "us-east-1"}
    }
  }')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    if echo "$BODY" | jq -e '.result' > /dev/null 2>&1; then
        echo "   ✅ tools/call succeeded (HTTP $HTTP_CODE)"
        echo "   Result preview:"
        echo "$BODY" | jq '.result' | head -20
    else
        echo "   ❌ tools/call returned 200 but invalid response"
        echo "$BODY" | jq .
        exit 1
    fi
else
    echo "   ❌ tools/call failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ GATEWAY IS WORKING CORRECTLY"
echo "=========================================="
echo ""
echo "Gateway URL: $GATEWAY_URL"
echo "Status: Ready for use in Lambda"
