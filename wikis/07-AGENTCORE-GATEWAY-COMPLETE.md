# Layer 7: AgentCore Gateway - Complete Guide

## What Is AgentCore Gateway?

**AgentCore Gateway** is a managed service that:
- Exposes MCP (Model Context Protocol) servers as HTTP endpoints
- Handles authentication (OAuth/Cognito)
- Routes requests to backend MCP servers
- Manages connections and scaling

```
Security Lambda → AgentCore Gateway → MCP Server → AWS Security Services
```

## Your Current Setup

**Gateway ID:** `security-chatbot-gateway-41f3cc60`
**Gateway URL:** `https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp`
**MCP Server:** Well-Architected Security MCP Server
**Authentication:** Cognito OAuth (client credentials)

## Issues You Faced

### Issue 1: Multiple Gateway Versions/Aliases
**Problem:** Lost track of which Gateway URL to use
**Solution:** Track in `agent-state.json`

### Issue 2: Gateway Not Ready After Deployment
**Problem:** 503 errors, takes 30-60s to become ready
**Solution:** Wait for READY status + 15s stabilization

### Issue 3: OAuth Token Issues
**Problem:** Token expired, wrong scopes, authentication failures
**Solution:** Get fresh token each time, verify scopes

### Issue 4: Wrong Gateway URL in Lambda
**Problem:** Hardcoded old URL
**Solution:** Use environment variable

## AgentCore Gateway Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentCore Gateway                         │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   OAuth      │    │   Request    │    │   Response   │ │
│  │   Validator  │ -> │   Router     │ -> │   Formatter  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│                              │                               │
└──────────────────────────────┼───────────────────────────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │   MCP Server         │
                    │   (Security Tools)   │
                    └──────────────────────┘
```

## Gateway Configuration

### Runtime Configuration

Your Gateway is configured with:

```json
{
  "runtimeConfig": {
    "mcpServers": {
      "SecurityMCPServer": {
        "command": "uv",
        "args": [
          "--directory",
          "/path/to/well-architected-security-mcp-server",
          "run",
          "server.py"
        ],
        "env": {
          "AWS_REGION": "us-east-1"
        }
      }
    }
  }
}
```

### Authentication Configuration

```json
{
  "authConfig": {
    "type": "COGNITO_USER_POOLS",
    "cognitoUserPoolArn": "arn:aws:cognito-idp:us-east-1:ACCOUNT:userpool/POOL_ID",
    "clientId": "6aarhftf6bopppar05humcp2r6"
  }
}
```

## Gateway Operations

### Check Gateway Status

```bash
# Using AgentCore CLI
agentcore gateway describe --gateway-id security-chatbot-gateway-41f3cc60

# Expected output
{
  "gatewayId": "security-chatbot-gateway-41f3cc60",
  "status": "READY",
  "url": "https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
  "version": "1",
  "lastUpdated": "2025-10-19T06:00:00Z"
}
```

### List Available Tools

```bash
# Get OAuth token
TOKEN=$(curl -X POST "$TOKEN_URL" \
  -H "Authorization: Basic $(echo -n "$CLIENT_ID:" | base64)" \
  -d "grant_type=client_credentials" \
  | jq -r '.access_token')

# List tools
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' | jq .
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "SecurityMCPTools___CheckSecurityServices",
        "description": "Check status of AWS security services",
        "inputSchema": {
          "type": "object",
          "properties": {
            "region": {"type": "string"},
            "services": {"type": "array"}
          }
        }
      },
      {
        "name": "SecurityMCPTools___GetSecurityFindings",
        "description": "Get security findings",
        "inputSchema": {
          "type": "object",
          "properties": {
            "region": {"type": "string"},
            "service": {"type": "string"},
            "severity_filter": {"type": "string"}
          }
        }
      }
    ]
  }
}
```

### Call a Tool

```bash
# Call CheckSecurityServices
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "SecurityMCPTools___CheckSecurityServices",
      "arguments": {
        "region": "us-east-1",
        "services": ["guardduty", "securityhub"]
      }
    }
  }' | jq .
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "services": [
      {
        "name": "guardduty",
        "enabled": true,
        "status": "ACTIVE"
      },
      {
        "name": "securityhub",
        "enabled": true,
        "status": "ACTIVE"
      }
    ]
  }
}
```

## Gateway Deployment

### Deploy New Gateway

```bash
#!/bin/bash
# deploy-gateway.sh

# Create runtime config
cat > runtime-config.json << 'EOF'
{
  "mcpServers": {
    "SecurityMCPServer": {
      "command": "uv",
      "args": [
        "--directory",
        "/persistent/home/ubuntu/workspace/well-arch-sec-mcp-server-tets/mcp/src/well-architected-security-mcp-server/awslabs/well_architected_security_mcp_server",
        "run",
        "server.py"
      ],
      "env": {
        "AWS_REGION": "us-east-1",
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
EOF

# Deploy Gateway
agentcore gateway deploy \
  --gateway-name SecurityChatbotGateway \
  --runtime-config file://runtime-config.json \
  --auth-type COGNITO_USER_POOLS \
  --cognito-user-pool-arn "arn:aws:cognito-idp:us-east-1:ACCOUNT:userpool/POOL_ID" \
  --cognito-client-id "6aarhftf6bopppar05humcp2r6"

# Wait for READY
agentcore gateway wait --gateway-id GATEWAY_ID --status READY

# Stabilization wait
sleep 15

# Get Gateway URL
GATEWAY_URL=$(agentcore gateway describe --gateway-id GATEWAY_ID --query 'url' --output text)
echo "Gateway URL: $GATEWAY_URL"

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --environment Variables="{GATEWAY_URL=$GATEWAY_URL,...}"
```

### Update Gateway

```bash
#!/bin/bash
# update-gateway.sh

GATEWAY_ID="security-chatbot-gateway-41f3cc60"

# Update runtime config
agentcore gateway update \
  --gateway-id "$GATEWAY_ID" \
  --runtime-config file://runtime-config.json

# Wait for READY
agentcore gateway wait --gateway-id "$GATEWAY_ID" --status READY

# Stabilization wait
sleep 15

echo "✅ Gateway updated and ready"
```

## Gateway Testing

### Test Script

```bash
#!/bin/bash
# test-gateway.sh

GATEWAY_URL="$1"
TOKEN="$2"

if [ -z "$GATEWAY_URL" ] || [ -z "$TOKEN" ]; then
    echo "Usage: ./test-gateway.sh <gateway-url> <token>"
    exit 1
fi

echo "Testing Gateway: $GATEWAY_URL"
echo ""

# Test 1: List tools
echo "1. Testing tools/list..."
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
    echo "   ✅ tools/list succeeded"
    echo "$BODY" | jq -r '.result.tools[].name'
else
    echo "   ❌ tools/list failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
    exit 1
fi

echo ""

# Test 2: Call CheckSecurityServices
echo "2. Testing CheckSecurityServices..."
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
    echo "   ✅ CheckSecurityServices succeeded"
    echo "$BODY" | jq '.result' | head -20
else
    echo "   ❌ CheckSecurityServices failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq .
    exit 1
fi

echo ""
echo "✅ Gateway is working correctly"
```

**Usage:**
```bash
# Get token
TOKEN=$(curl -X POST "$TOKEN_URL" \
  -H "Authorization: Basic $(echo -n "$CLIENT_ID:" | base64)" \
  -d "grant_type=client_credentials" \
  | jq -r '.access_token')

# Test Gateway
./scripts/test-gateway.sh "$GATEWAY_URL" "$TOKEN"
```

## Gateway Monitoring

### Check Gateway Metrics

```bash
# Get Gateway metrics
agentcore gateway get-metrics \
  --gateway-id GATEWAY_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)
```

**Metrics:**
- Request count
- Error rate
- Latency (p50, p90, p99)
- Token validation failures

### Check Gateway Logs

```bash
# Get Gateway logs (if available)
agentcore gateway logs \
  --gateway-id GATEWAY_ID \
  --tail 100 \
  --follow
```

## Common Gateway Errors

### Error: 503 Service Unavailable
**Cause:** Gateway not ready yet
**Fix:** Wait for READY status + 15s stabilization

### Error: 401 Unauthorized
**Cause:** Missing or invalid OAuth token
**Fix:** Get fresh token, check token format

### Error: 403 Forbidden
**Cause:** Token doesn't have required scopes
**Fix:** Update Cognito client scopes

### Error: 404 Not Found
**Cause:** Wrong Gateway URL or tool name
**Fix:** Verify URL, check tool name with tools/list

### Error: 500 Internal Server Error
**Cause:** MCP server error or Gateway error
**Fix:** Check Gateway logs, verify MCP server running

### Error: Timeout
**Cause:** MCP server taking too long
**Fix:** Increase Lambda timeout, check MCP server performance

## Gateway State Tracking

**Add to `agent-state.json`:**

```json
{
  "agentcore_gateway": {
    "gateway_id": "security-chatbot-gateway-41f3cc60",
    "gateway_name": "SecurityChatbotGateway",
    "active_url": "https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
    "version": "1",
    "alias": "prod",
    "status": "READY",
    "last_updated": "2025-10-19T06:00:00Z",
    "mcp_server": {
      "name": "SecurityMCPServer",
      "path": "/persistent/home/ubuntu/workspace/well-arch-sec-mcp-server-tets/mcp/src/well-architected-security-mcp-server",
      "command": "uv run server.py"
    },
    "tools": [
      "SecurityMCPTools___CheckSecurityServices",
      "SecurityMCPTools___GetSecurityFindings",
      "SecurityMCPTools___CheckStorageEncryption",
      "SecurityMCPTools___CheckNetworkSecurity",
      "SecurityMCPTools___ListServicesInRegion",
      "SecurityMCPTools___GetStoredSecurityContext"
    ]
  }
}
```

## Gateway Checklist

Before using Gateway:

- [ ] Gateway deployed and status is READY
- [ ] Gateway URL saved in environment variable
- [ ] OAuth token can be obtained successfully
- [ ] Token has required scopes
- [ ] Gateway tested with tools/list
- [ ] Gateway tested with tools/call
- [ ] Lambda has correct Gateway URL
- [ ] Lambda timeout ≥ 60 seconds
- [ ] Waited 15s after Gateway deployment
- [ ] State file updated with Gateway info

## Integration with Lambda

**Lambda calls Gateway:**

```python
import requests
import os

def call_gateway(tool_name, arguments):
    """Call AgentCore Gateway MCP tool"""
    
    # Get OAuth token
    token = get_oauth_token()
    
    # Build MCP request
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    # Call Gateway
    gateway_url = os.environ['GATEWAY_URL']
    response = requests.post(
        gateway_url,
        json=mcp_request,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        timeout=45
    )
    
    if response.status_code == 200:
        result = response.json()
        return result.get('result', {})
    else:
        raise Exception(f"Gateway error: {response.status_code} - {response.text}")
```

## Related Documentation

- [AgentCore Gateway Issues](./AGENTCORE-GATEWAY-ISSUES.md) - Troubleshooting
- [OAuth/Cognito Issues](./OAUTH-COGNITO-TOKEN-ISSUES.md) - Authentication
- [Complete Parameter Mapping](./COMPLETE-PARAMETER-MAPPING.md) - Parameter handling
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md) - Master issues list
