# AgentCore Gateway - Version, Alias, and Readiness Issues

## Issues You Faced

### Issue 1: Multiple Gateway Versions/Aliases Confusion
**Symptom:** Multiple Gateway URLs, not sure which one to use
**Root Cause:** AgentCore creates versions and aliases, lost track of active one

**Example confusion:**
```
https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
https://security-chatbot-gateway-41f3cc60-v2-abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
https://security-chatbot-gateway-41f3cc60-prod-xyz789.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp
```

**Which one is active?**

**Solution:**
```bash
# List all gateways
agentcore gateway list

# Get gateway details
agentcore gateway describe --gateway-id GATEWAY_ID

# Check which alias is active
agentcore gateway list-aliases --gateway-id GATEWAY_ID
```

**Track in state file:**
```json
{
  "agentcore_gateway": {
    "gateway_id": "security-chatbot-gateway-41f3cc60",
    "active_url": "https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
    "version": "1",
    "alias": "prod",
    "last_updated": "2025-10-19T06:00:00Z"
  }
}
```

**Prevention:** Maintain single source of truth for Gateway URL

---

### Issue 2: Gateway Not Ready After Deployment
**Symptom:** Gateway deployed but returns 503 Service Unavailable
**Root Cause:** Gateway takes time to become ready (30-60s)

**Solution:**
```bash
# After deploying Gateway
agentcore gateway deploy ...

# Wait for ready status
agentcore gateway wait --gateway-id GATEWAY_ID --status READY

# Or manual check
while true; do
  STATUS=$(agentcore gateway describe --gateway-id GATEWAY_ID --query 'status' --output text)
  echo "Status: $STATUS"
  if [ "$STATUS" = "READY" ]; then
    echo "Gateway is ready"
    break
  fi
  sleep 10
done

# Additional stabilization wait
sleep 15
```

**Prevention:** Always wait for READY status + 15s stabilization before testing

---

### Issue 3: Gateway Failing Repeatedly After Changes
**Symptom:** Gateway works, make changes, then fails repeatedly
**Root Cause:** 
- Old version still cached
- New version not fully deployed
- DNS propagation lag

**Solution:**
```bash
# 1. Check Gateway status
agentcore gateway describe --gateway-id GATEWAY_ID

# 2. If status is FAILED or UPDATING, wait
agentcore gateway wait --gateway-id GATEWAY_ID --status READY

# 3. Clear any cached connections
# (Lambda will get new connection on next invocation)

# 4. Test Gateway directly
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

**Prevention:** 
- Wait for READY status after every change
- Test Gateway directly before testing full flow
- Don't make multiple rapid changes

---

### Issue 4: Wrong Gateway URL in Lambda
**Symptom:** Lambda calls Gateway but gets 404 or connection refused
**Root Cause:** Hardcoded old Gateway URL in Lambda code

**Current code problem:**
```python
# Hardcoded URL - WRONG
gateway_url = "https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
```

**Solution:**
```python
# Use environment variable
gateway_url = os.environ.get('GATEWAY_URL')
if not gateway_url:
    raise ValueError("GATEWAY_URL environment variable not set")
```

**Update Lambda:**
```bash
# Get current Gateway URL
GATEWAY_URL=$(agentcore gateway describe --gateway-id GATEWAY_ID --query 'url' --output text)

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --environment Variables="{GATEWAY_URL=$GATEWAY_URL,COGNITO_CLIENT_ID=...,TOKEN_URL=...}"
```

**Prevention:** Never hardcode Gateway URL, always use environment variable

---

### Issue 5: Gateway Version Mismatch
**Symptom:** Lambda calls Gateway but gets unexpected response format
**Root Cause:** Gateway updated to new version with different API

**Solution:**
```bash
# Check Gateway version
agentcore gateway describe --gateway-id GATEWAY_ID --query 'version'

# Check what changed in new version
agentcore gateway describe-version --gateway-id GATEWAY_ID --version VERSION

# If API changed, update Lambda code to match
```

**Prevention:** 
- Pin Gateway to specific version/alias
- Test after Gateway updates
- Review Gateway changelog before updating

---

### Issue 6: Gateway Timeout
**Symptom:** Lambda times out waiting for Gateway response
**Root Cause:** Gateway processing takes longer than Lambda timeout

**Solution:**
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --timeout 60

# Increase request timeout in code
response = requests.post(
    gateway_url,
    json=request_data,
    headers={'Authorization': f'Bearer {token}'},
    timeout=45  # Less than Lambda timeout
)
```

**Prevention:** 
- Lambda timeout: 60s
- Request timeout: 45s (leave buffer)
- Gateway operations: Should complete in <30s

---

### Issue 7: Gateway Authentication Failing
**Symptom:** Gateway returns 401 Unauthorized or 403 Forbidden
**Root Cause:** 
- Token doesn't have required scopes
- Gateway updated with new auth requirements
- Token expired

**Solution:**
```bash
# 1. Get fresh token
TOKEN=$(curl -X POST "$TOKEN_URL" \
  -H "Authorization: Basic $(echo -n "$CLIENT_ID:" | base64)" \
  -d "grant_type=client_credentials" \
  | jq -r '.access_token')

# 2. Decode token to check scopes
echo "$TOKEN" | cut -d. -f2 | base64 -d | jq .

# 3. Check Gateway auth requirements
agentcore gateway describe --gateway-id GATEWAY_ID --query 'authConfig'

# 4. Update Cognito client scopes if needed
aws cognito-idp update-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID \
  --allowed-o-auth-scopes "gateway-resource-server/invoke"
```

**Prevention:** 
- Verify token scopes match Gateway requirements
- Get fresh token on every Lambda invocation
- Test Gateway auth separately before full flow

---

## Gateway Readiness Checklist

Before calling Gateway from Lambda:

- [ ] Gateway status is READY
- [ ] Gateway URL is correct and in environment variable
- [ ] OAuth token obtained successfully
- [ ] Token has required scopes
- [ ] Gateway tested directly with curl
- [ ] Lambda timeout ≥ 60s
- [ ] Request timeout < Lambda timeout
- [ ] Waited 15s after Gateway deployment

---

## Gateway Testing Script

```bash
#!/bin/bash
# test-gateway.sh - Test Gateway before using in Lambda

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
RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }')

if echo "$RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo "   ✅ tools/list succeeded"
    echo "$RESPONSE" | jq '.result.tools[].name'
else
    echo "   ❌ tools/list failed"
    echo "$RESPONSE" | jq .
    exit 1
fi

echo ""

# Test 2: Call a tool
echo "2. Testing tools/call..."
RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
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

if echo "$RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo "   ✅ tools/call succeeded"
    echo "$RESPONSE" | jq '.result' | head -20
else
    echo "   ❌ tools/call failed"
    echo "$RESPONSE" | jq .
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
./test-gateway.sh "$GATEWAY_URL" "$TOKEN"
```

---

## Gateway State Tracking

**Add to `templates/agent-state.json`:**
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
    "tools": [
      "SecurityMCPTools___CheckSecurityServices",
      "SecurityMCPTools___GetSecurityFindings",
      "SecurityMCPTools___CheckStorageEncryption"
    ]
  },
  "cognito": {
    "user_pool_id": "us-east-1_XXXXXXXXX",
    "client_id": "6aarhftf6bopppar05humcp2r6",
    "domain": "security-chatbot-oauth-domain",
    "token_url": "https://security-chatbot-oauth-domain.auth.us-east-1.amazoncognito.com/oauth2/token"
  }
}
```

---

## Gateway Deployment Workflow

```bash
# 1. Deploy Gateway
agentcore gateway deploy \
  --gateway-name SecurityChatbotGateway \
  --runtime-config file://runtime-config.json

# 2. Wait for READY
agentcore gateway wait --gateway-id GATEWAY_ID --status READY

# 3. Stabilization wait
sleep 15

# 4. Get Gateway URL
GATEWAY_URL=$(agentcore gateway describe --gateway-id GATEWAY_ID --query 'url' --output text)

# 5. Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --environment Variables="{GATEWAY_URL=$GATEWAY_URL,...}"

# 6. Get OAuth token
TOKEN=$(curl -X POST "$TOKEN_URL" ...)

# 7. Test Gateway
./test-gateway.sh "$GATEWAY_URL" "$TOKEN"

# 8. Update state file
vim templates/agent-state.json
# Update gateway_url, version, last_updated

# 9. Test full flow
# (React → API Gateway → Web API Lambda → Bedrock Agent → Security Lambda → Gateway)
```

---

## Common Gateway Errors

### Error: 503 Service Unavailable
**Cause:** Gateway not ready yet
**Fix:** Wait for READY status + 15s

### Error: 404 Not Found
**Cause:** Wrong Gateway URL or endpoint
**Fix:** Verify URL, check `/mcp` endpoint

### Error: 401 Unauthorized
**Cause:** Missing or invalid token
**Fix:** Get fresh token, check scopes

### Error: 403 Forbidden
**Cause:** Token doesn't have required scopes
**Fix:** Update Cognito client scopes

### Error: 500 Internal Server Error
**Cause:** Gateway error processing request
**Fix:** Check Gateway logs, verify request format

### Error: Timeout
**Cause:** Gateway taking too long
**Fix:** Increase Lambda timeout, check Gateway performance

---

## Gateway Monitoring

```bash
# Check Gateway status
agentcore gateway describe --gateway-id GATEWAY_ID

# Check Gateway metrics
agentcore gateway get-metrics \
  --gateway-id GATEWAY_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)

# Check Gateway logs (if available)
agentcore gateway logs --gateway-id GATEWAY_ID --tail 100
```

---

## Related Documentation

- [OAuth/Cognito Token Issues](./OAUTH-COGNITO-TOKEN-ISSUES.md)
- [IAM vs OAuth Decision](./IAM-VS-OAUTH-DECISION.md)
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md)
- [Security Lambda Fixed Code](../templates/gateway-proxy-lambda-fixed.py)
