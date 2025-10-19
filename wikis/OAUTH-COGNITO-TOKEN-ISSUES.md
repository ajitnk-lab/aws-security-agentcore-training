# OAuth, Cognito, and Token Issues - Security Lambda

## Issues You Faced

### Issue 1: Token Getting Expired
**Symptom:** Lambda works first time, then fails with 401 Unauthorized
**Root Cause:** Token cached/reused but expired (default 1 hour)

**Current Code Problem:**
```python
# Gets token on EVERY invocation - CORRECT approach
token_response = requests.post(token_url, ...)
token = token_response.json()['access_token']
```

**This is actually CORRECT** - getting fresh token each time prevents expiration issues.

**If you're still seeing expiration:**
- Token might be cached somewhere else (API Gateway, client side)
- Check token expiration time in Cognito settings

---

### Issue 2: OAuth Token Request Failing
**Symptom:** `Failed to get OAuth token: 400` or `401`
**Root Causes:**

#### 2a. Wrong Client Credentials
```python
client_id = '6aarhftf6bopppar05humcp2r6'
client_secret = ''  # Empty - is this correct?
```

**Check:**
```bash
# Verify client exists and settings
aws cognito-idp describe-user-pool-client \
  --user-pool-id us-east-1_XXXXXXXXX \
  --client-id 6aarhftf6bopppar05humcp2r6
```

**Look for:**
- `AllowedOAuthFlows`: Should include `"client_credentials"`
- `AllowedOAuthScopes`: Should match what Gateway expects
- `ClientSecret`: If present, must be used in request

#### 2b. Wrong Token URL
```python
token_url = "https://security-chatbot-oauth-domain.auth.us-east-1.amazoncognito.com/oauth2/token"
```

**Verify:**
```bash
# Check Cognito domain
aws cognito-idp describe-user-pool \
  --user-pool-id us-east-1_XXXXXXXXX \
  | jq '.UserPool.Domain'
```

**Correct format:**
- Custom domain: `https://YOUR-DOMAIN.auth.REGION.amazoncognito.com/oauth2/token`
- Cognito domain: `https://YOUR-POOL-DOMAIN.auth.REGION.amazoncognito.com/oauth2/token`

#### 2c. Client Not Configured for Client Credentials Flow
**Check Cognito client settings:**
```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID \
  | jq '.UserPoolClient.AllowedOAuthFlows'
```

**Expected:** `["client_credentials"]`

**If missing, update:**
```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID \
  --allowed-o-auth-flows client_credentials \
  --allowed-o-auth-flows-user-pool-client
```

---

### Issue 3: Wrong OAuth Scopes
**Symptom:** Token obtained but Gateway rejects with 403 Forbidden
**Root Cause:** Token doesn't have required scopes for Gateway

**Check current scopes:**
```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID \
  | jq '.UserPoolClient.AllowedOAuthScopes'
```

**For AgentCore Gateway, you need:**
- Resource server scope (e.g., `gateway-resource-server/invoke`)
- Or custom scopes defined in your setup

**Update scopes:**
```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID \
  --allowed-o-auth-scopes "gateway-resource-server/invoke"
```

---

### Issue 4: Base64 Encoding Issues
**Current code:**
```python
credentials = f"{client_id}:{client_secret}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
```

**If client_secret is empty:**
```python
# Still need the colon
credentials = f"{client_id}:"  # Note the colon
encoded_credentials = base64.b64encode(credentials.encode()).decode()
```

**Test encoding:**
```python
import base64
client_id = '6aarhftf6bopppar05humcp2r6'
client_secret = ''
credentials = f"{client_id}:{client_secret}"
encoded = base64.b64encode(credentials.encode()).decode()
print(f"Authorization: Basic {encoded}")
```

---

### Issue 5: Token Request Timeout
**Symptom:** `requests.exceptions.Timeout`
**Root Cause:** Cognito endpoint unreachable or slow

**Current code:**
```python
token_response = requests.post(token_url, ..., timeout=10)
```

**Solutions:**
1. Increase timeout to 30s
2. Add retry logic
3. Check VPC/security group if Lambda in VPC

**With retry:**
```python
import time

def get_token_with_retry(token_url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                token_url,
                headers=headers,
                data=data,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()['access_token']
            
            print(f"Token request failed: {response.status_code} - {response.text}")
            
        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
    
    raise Exception("Failed to get token after retries")
```

---

### Issue 6: Lambda in VPC Can't Reach Cognito
**Symptom:** Token request times out or fails with connection error
**Root Cause:** Lambda in VPC without NAT Gateway or VPC endpoints

**Check if Lambda in VPC:**
```bash
aws lambda get-function-configuration \
  --function-name bedrock-gateway-proxy \
  | jq '.VpcConfig'
```

**If in VPC, you need:**
1. **NAT Gateway** (for internet access), OR
2. **VPC Endpoint for Cognito** (not available - must use NAT)

**Solution:**
```bash
# Option 1: Remove Lambda from VPC (if not needed)
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --vpc-config SubnetIds=[],SecurityGroupIds=[]

# Option 2: Add NAT Gateway to VPC
# (requires VPC configuration changes)
```

---

### Issue 7: Token Caching Gone Wrong
**Symptom:** First invocation works, subsequent fail
**Root Cause:** Trying to cache token but not checking expiration

**DON'T DO THIS:**
```python
# Global variable - BAD
cached_token = None

def lambda_handler(event, context):
    global cached_token
    if not cached_token:
        cached_token = get_token()  # Never refreshes!
```

**DO THIS (current code is correct):**
```python
def lambda_handler(event, context):
    # Get fresh token every time
    token = get_token()
    # Use token
```

**If you MUST cache (for performance):**
```python
import time

token_cache = {'token': None, 'expires_at': 0}

def get_cached_token():
    now = time.time()
    if token_cache['token'] and now < token_cache['expires_at']:
        return token_cache['token']
    
    # Get new token
    response = requests.post(...)
    token_data = response.json()
    
    token_cache['token'] = token_data['access_token']
    # Expire 5 minutes before actual expiration
    token_cache['expires_at'] = now + token_data.get('expires_in', 3600) - 300
    
    return token_cache['token']
```

---

## Debugging OAuth Issues

### Step 1: Test Token Request Manually
```bash
# Get token using curl
CLIENT_ID="6aarhftf6bopppar05humcp2r6"
CLIENT_SECRET=""
TOKEN_URL="https://security-chatbot-oauth-domain.auth.us-east-1.amazoncognito.com/oauth2/token"

# Encode credentials
CREDENTIALS=$(echo -n "$CLIENT_ID:$CLIENT_SECRET" | base64)

# Request token
curl -X POST "$TOKEN_URL" \
  -H "Authorization: Basic $CREDENTIALS" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials"
```

**Expected response:**
```json
{
  "access_token": "eyJraWQ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

**Common errors:**
- `400 Bad Request` - Wrong credentials or grant_type
- `401 Unauthorized` - Invalid client_id or client_secret
- `403 Forbidden` - Client not allowed to use client_credentials flow

### Step 2: Decode Token to Check Scopes
```bash
# Copy access_token from above
TOKEN="eyJraWQ..."

# Decode (token has 3 parts separated by dots)
echo "$TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq .
```

**Check:**
- `scope`: Should match what Gateway expects
- `exp`: Expiration timestamp
- `client_id`: Should match your client

### Step 3: Test Gateway with Token
```bash
TOKEN="eyJraWQ..."
GATEWAY_URL="https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

curl -X POST "$GATEWAY_URL" \
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
  }'
```

**Expected:** Gateway response with results
**If 401/403:** Token doesn't have required scopes

---

## Fixed Lambda Code with Better Error Handling

```python
import json
import os
import requests
import base64
import time

def get_oauth_token():
    """Get OAuth token with retry logic"""
    client_id = os.environ.get('COGNITO_CLIENT_ID')
    client_secret = os.environ.get('COGNITO_CLIENT_SECRET', '')
    token_url = os.environ.get('TOKEN_URL')
    
    if not client_id or not token_url:
        raise ValueError("Missing COGNITO_CLIENT_ID or TOKEN_URL environment variables")
    
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    for attempt in range(3):
        try:
            response = requests.post(
                token_url,
                headers={
                    'Authorization': f'Basic {encoded_credentials}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data='grant_type=client_credentials',
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                print(f"Token obtained successfully (expires in {token_data.get('expires_in')}s)")
                return token_data['access_token']
            
            print(f"Token request failed (attempt {attempt + 1}): {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code in [400, 401, 403]:
                # Don't retry auth errors
                raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
            
        except requests.exceptions.Timeout:
            print(f"Token request timeout (attempt {attempt + 1})")
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise Exception("Token request timed out after retries")
        
        except requests.exceptions.RequestException as e:
            print(f"Token request error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
    
    raise Exception("Failed to get token after 3 attempts")


def lambda_handler(event, context):
    try:
        # Get fresh token
        token = get_oauth_token()
        
        # Rest of your code...
        
    except Exception as e:
        print(f"Error: {e}")
        return error_response(event, str(e))
```

---

## Checklist: OAuth/Cognito Setup

- [ ] Cognito user pool exists
- [ ] Cognito app client created
- [ ] App client has `client_credentials` in AllowedOAuthFlows
- [ ] App client has required scopes in AllowedOAuthScopes
- [ ] Domain configured for user pool
- [ ] Token URL is correct format
- [ ] Client ID is correct
- [ ] Client secret is correct (or empty if public client)
- [ ] Lambda has environment variables set
- [ ] Lambda NOT in VPC (or has NAT Gateway)
- [ ] Token request tested manually with curl
- [ ] Token decoded to verify scopes
- [ ] Gateway tested with token

---

## Related Documentation

- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md)
- [Security Lambda Fixed Code](../templates/gateway-proxy-lambda-fixed.py)
