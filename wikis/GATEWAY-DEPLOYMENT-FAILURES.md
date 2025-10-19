# Gateway Deployment Failures - Real Problems & Solutions

## The 3 Critical Failures You Had

### Failure 1: Gateway Needs HTTP Endpoint, Not ARN ❌

**What You Tried:**
```python
# WRONG - Gave Lambda ARN
gateway = client.setup_gateway(
    gateway_name="security-gateway",
    target_source="arn:aws:lambda:us-east-1:123:function:SecurityLambda",  # ❌ WRONG
    target_type='lambda'
)
```

**Why It Failed:**
Gateway expects:
- **For MCP Server**: Runtime HTTP endpoint (e.g., `http://runtime-url/invocations`)
- **For Lambda**: Lambda config JSON with ARN + tool schemas
- **For OpenAPI**: OpenAPI spec (inline JSON or S3 URL)

**Correct Approach:**

**Option A: Use AgentCore Runtime (Recommended)**
```python
# Step 1: Deploy MCP server to AgentCore Runtime
agentcore configure --entrypoint server.py
agentcore launch  # Returns HTTP endpoint

# Step 2: Create Gateway pointing to Runtime endpoint
gateway = client.setup_gateway(
    gateway_name="security-gateway",
    target_source="http://runtime-abc123.agentcore.us-east-1.amazonaws.com/invocations",  # ✅ HTTP endpoint
    target_type='runtime',
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config']
)
```

**Option B: Use Lambda with Tool Config**
```python
# Define Lambda with tool schemas
lambda_config = {
    "arn": "arn:aws:lambda:us-east-1:123:function:SecurityLambda",
    "tools": [
        {
            "name": "CheckSecurityServices",
            "description": "Check AWS security services",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "region": {"type": "string"},
                    "services": {"type": "array"}
                }
            }
        }
    ]
}

# Create Gateway with Lambda config
gateway = client.setup_gateway(
    gateway_name="security-gateway",
    target_source=json.dumps(lambda_config),  # ✅ JSON config, not ARN
    target_type='lambda',
    execution_role_arn=role_arn,
    authorizer_config=cognito['authorizer_config']
)
```

---

### Failure 2: Didn't Know Which Version/Alias to Attach ❌

**The Confusion:**
- Gateway has versions (1, 2, 3...)
- Gateway has aliases (prod, dev, test...)
- Runtime has versions
- Agent has versions
- Which one to use where?

**The Truth:**

**Gateway Versions/Aliases:**
- Gateway creates version automatically on each update
- Alias points to a specific version
- **You don't manually attach versions** - Gateway manages this

**Runtime Versions/Aliases:**
- Runtime creates version on each `agentcore launch`
- Alias points to a specific runtime version
- **Gateway connects to Runtime via HTTP endpoint** - version is in the URL

**Agent Versions/Aliases:**
- Agent has DRAFT and numbered versions (1, 2, 3...)
- Agent alias points to agent version
- **Agent doesn't connect directly to Gateway** - Lambda does

**Correct Flow:**

```
1. Deploy Runtime:
   agentcore launch
   → Returns: http://runtime-v1-abc123.agentcore.us-east-1.amazonaws.com/invocations

2. Create Gateway pointing to Runtime:
   gateway = client.setup_gateway(
       target_source="http://runtime-v1-abc123.agentcore.us-east-1.amazonaws.com/invocations"
   )
   → Returns: Gateway URL with version in it

3. Lambda uses Gateway URL:
   GATEWAY_URL = "https://gateway-abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

4. Agent calls Lambda:
   Agent → Lambda → Gateway → Runtime → MCP Server
```

**No manual version attachment needed!**

---

### Failure 3: OAuth/Token/Client ID Problems ❌

**Problems You Had:**

#### 3a. Wrong Client ID Format
```python
# WRONG - Used Cognito User Pool ID
client_id = "us-east-1_XXXXXXXXX"  # ❌ This is pool ID, not client ID
```

**Fix:**
```bash
# Get correct client ID
aws cognito-idp list-user-pool-clients \
  --user-pool-id us-east-1_XXXXXXXXX \
  | jq '.UserPoolClients[].ClientId'

# Use the client ID (looks like: 6aarhftf6bopppar05humcp2r6)
client_id = "6aarhftf6bopppar05humcp2r6"  # ✅ Correct
```

#### 3b. Token Expiry Not Handled
```python
# WRONG - Token cached forever
token = get_token_once()
# Use token forever... ❌ Expires after 1 hour
```

**Fix:**
```python
# Get fresh token on every Lambda invocation
def lambda_handler(event, context):
    token = get_oauth_token()  # ✅ Fresh token each time
    # Use token...
```

#### 3c. Wrong Token Endpoint
```python
# WRONG - Used wrong domain
token_url = "https://cognito-idp.us-east-1.amazonaws.com/..."  # ❌ Wrong
```

**Fix:**
```bash
# Get correct token endpoint
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-1_XXXXXXXXX \
  | jq '.UserPool.Domain'

# Use OAuth endpoint
token_url = "https://YOUR-DOMAIN.auth.us-east-1.amazoncognito.com/oauth2/token"  # ✅ Correct
```

#### 3d. Missing OAuth Scopes
```python
# Token obtained but Gateway rejects with 403
```

**Fix:**
```bash
# Check required scopes
agentcore gateway describe --gateway-id GATEWAY_ID | jq '.authConfig.scopes'

# Update Cognito client with required scopes
aws cognito-idp update-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID \
  --allowed-o-auth-scopes "gateway-resource-server/invoke"
```

---

## Complete Working Solution

### Step 1: Deploy MCP Server to AgentCore Runtime

```bash
#!/bin/bash
# deploy-mcp-to-runtime.sh

cd /path/to/mcp/server

# Install AgentCore CLI
pip install bedrock-agentcore-starter-toolkit

# Configure
agentcore configure \
  --entrypoint server.py \
  --non-interactive

# Deploy
agentcore launch

# Get Runtime endpoint
RUNTIME_ENDPOINT=$(agentcore runtime describe --query 'endpoint' --output text)
echo "Runtime Endpoint: $RUNTIME_ENDPOINT"

# Save to file
echo "$RUNTIME_ENDPOINT" > runtime-endpoint.txt
```

### Step 2: Create Gateway with Python SDK

```python
#!/usr/bin/env python3
# create-gateway.py

from bedrock_agentcore.gateway import GatewayClient
import json

# Read Runtime endpoint
with open('runtime-endpoint.txt', 'r') as f:
    runtime_endpoint = f.read().strip()

# Initialize Gateway client
client = GatewayClient(region_name='us-east-1')

# Create OAuth authorizer with Cognito
cognito = client.create_oauth_authorizer_with_cognito("security-chatbot")

# Create Gateway pointing to Runtime
gateway = client.setup_gateway(
    gateway_name="security-chatbot-gateway",
    target_source=runtime_endpoint,  # HTTP endpoint from Runtime
    target_type='runtime',
    execution_role_arn="arn:aws:iam::ACCOUNT:role/GatewayExecutionRole",
    authorizer_config=cognito['authorizer_config'],
    enable_semantic_search=True,
    description="Security chatbot gateway"
)

# Get Gateway URL
gateway_url = gateway.get_mcp_url()
print(f"Gateway URL: {gateway_url}")

# Get OAuth credentials
client_info = cognito['client_info']
print(f"Client ID: {client_info['client_id']}")
print(f"Token Endpoint: {client_info['token_endpoint']}")

# Save to file
with open('gateway-config.json', 'w') as f:
    json.dump({
        'gateway_url': gateway_url,
        'client_id': client_info['client_id'],
        'client_secret': client_info['client_secret'],
        'token_endpoint': client_info['token_endpoint'],
        'scope': client_info['scope']
    }, f, indent=2)

print("✅ Gateway created successfully")
print("Config saved to gateway-config.json")
```

### Step 3: Update Lambda with Gateway Config

```bash
#!/bin/bash
# update-lambda-config.sh

# Read Gateway config
GATEWAY_URL=$(jq -r '.gateway_url' gateway-config.json)
CLIENT_ID=$(jq -r '.client_id' gateway-config.json)
CLIENT_SECRET=$(jq -r '.client_secret' gateway-config.json)
TOKEN_URL=$(jq -r '.token_endpoint' gateway-config.json)

# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --environment Variables="{
    GATEWAY_URL=$GATEWAY_URL,
    COGNITO_CLIENT_ID=$CLIENT_ID,
    COGNITO_CLIENT_SECRET=$CLIENT_SECRET,
    TOKEN_URL=$TOKEN_URL
  }"

echo "✅ Lambda updated with Gateway config"
```

### Step 4: Test Complete Flow

```bash
#!/bin/bash
# test-complete-flow.sh

# Get OAuth token
TOKEN=$(curl -s -X POST "$(jq -r '.token_endpoint' gateway-config.json)" \
  -H "Authorization: Basic $(echo -n "$(jq -r '.client_id' gateway-config.json):$(jq -r '.client_secret' gateway-config.json)" | base64)" \
  -d "grant_type=client_credentials" \
  | jq -r '.access_token')

echo "Token obtained: ${TOKEN:0:20}..."

# Test Gateway
GATEWAY_URL=$(jq -r '.gateway_url' gateway-config.json)

curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }' | jq .

echo ""
echo "✅ Gateway test complete"
```

---

## Troubleshooting Checklist

### If Gateway Creation Fails:

- [ ] Runtime deployed and has HTTP endpoint?
- [ ] Runtime endpoint is HTTP URL, not ARN?
- [ ] Execution role has permissions?
- [ ] Cognito user pool exists?
- [ ] Using GatewayClient SDK correctly?

### If OAuth Fails:

- [ ] Using client ID (not pool ID)?
- [ ] Token endpoint is correct OAuth URL?
- [ ] Client has client_credentials flow enabled?
- [ ] Client has required scopes?
- [ ] Getting fresh token each time?

### If Gateway Can't Reach Runtime:

- [ ] Runtime is READY status?
- [ ] Runtime endpoint is accessible?
- [ ] Gateway execution role can invoke Runtime?
- [ ] No VPC/network issues?

---

## Key Lessons

1. **Gateway needs HTTP endpoint** - Not ARN, not Lambda function name
2. **Runtime provides HTTP endpoint** - Deploy MCP server to Runtime first
3. **No manual version attachment** - Gateway/Runtime manage versions automatically
4. **OAuth is complex** - Use SDK's `create_oauth_authorizer_with_cognito()` helper
5. **Test incrementally** - Runtime → Gateway → Lambda → Agent

---

## Related Files

- [AgentCore Gateway Complete](./07-AGENTCORE-GATEWAY-COMPLETE.md)
- [OAuth/Cognito Issues](./OAUTH-COGNITO-TOKEN-ISSUES.md)
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md)
