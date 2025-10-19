# IAM vs OAuth - When to Use What

## The Confusion You Faced

**Problem:** Kept switching between IAM and OAuth, repeated failures, not sure which to use where.

## Simple Decision Tree

```
┌─────────────────────────────────────┐
│ What are you calling?               │
└─────────────────────────────────────┘
                │
                ├─ AWS Service (S3, DynamoDB, etc.)
                │  → USE IAM
                │
                ├─ AgentCore Gateway
                │  → USE OAUTH (Cognito)
                │
                └─ Lambda (internal)
                   → USE IAM (execution role)
```

## Your Architecture - Which Auth Where

### Layer 1: React UI → API Gateway
**Auth:** None (public) OR Cognito User Pools (if you want user login)
**Why:** Frontend can't use IAM credentials securely

### Layer 2: API Gateway → Web API Lambda
**Auth:** IAM (Lambda execution role)
**Why:** Internal AWS service call

### Layer 3: Web API Lambda → Bedrock Agent
**Auth:** IAM (Lambda execution role with bedrock:InvokeAgent)
**Why:** AWS service call

### Layer 4: Bedrock Agent → Action Group
**Auth:** IAM (Agent service role)
**Why:** Internal Bedrock orchestration

### Layer 5: Action Group → Security Lambda (bedrock-gateway-proxy)
**Auth:** IAM (resource-based policy on Lambda)
**Why:** AWS service call

### Layer 6: Security Lambda → AgentCore Gateway
**Auth:** OAUTH (Cognito client credentials)
**Why:** AgentCore Gateway requires OAuth tokens

### Layer 7: AgentCore Gateway → AWS Security Services
**Auth:** IAM (Gateway's execution role)
**Why:** AWS service calls

## When to Use IAM

### ✅ Use IAM When:
1. **Calling AWS services** (S3, DynamoDB, Bedrock, Lambda, etc.)
2. **Lambda to Lambda** calls
3. **Lambda to AWS API** calls
4. **Service-to-service** within AWS

### How IAM Works:
```python
import boto3

# Boto3 automatically uses Lambda execution role
bedrock = boto3.client('bedrock-agent-runtime')
response = bedrock.invoke_agent(...)  # Uses IAM automatically
```

**No credentials in code** - IAM role attached to Lambda provides permissions.

### IAM Setup:
```bash
# Lambda execution role needs permission
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeAgent",
  "Resource": "arn:aws:bedrock:*:*:agent/*"
}
```

## When to Use OAuth

### ✅ Use OAuth When:
1. **Calling AgentCore Gateway**
2. **Calling external APIs** that require OAuth
3. **User authentication** (Cognito User Pools)

### How OAuth Works:
```python
import requests
import base64

# 1. Get token from Cognito
credentials = f"{client_id}:{client_secret}"
encoded = base64.b64encode(credentials.encode()).decode()

token_response = requests.post(
    token_url,
    headers={'Authorization': f'Basic {encoded}'},
    data='grant_type=client_credentials'
)
token = token_response.json()['access_token']

# 2. Use token to call Gateway
response = requests.post(
    gateway_url,
    headers={'Authorization': f'Bearer {token}'},
    json=request_data
)
```

**Credentials required** - Must get token first, then use in API calls.

### OAuth Setup:
```bash
# Cognito app client needs:
# - AllowedOAuthFlows: ["client_credentials"]
# - AllowedOAuthScopes: ["gateway-resource-server/invoke"]
```

## Common Mistakes You Made

### ❌ Mistake 1: Using OAuth for AWS Services
```python
# WRONG - Trying to use OAuth token for Bedrock
token = get_oauth_token()
bedrock = boto3.client('bedrock-agent-runtime')
response = bedrock.invoke_agent(
    headers={'Authorization': f'Bearer {token}'}  # WRONG!
)
```

**Fix:** Use IAM (boto3 handles automatically)
```python
# CORRECT - IAM via execution role
bedrock = boto3.client('bedrock-agent-runtime')
response = bedrock.invoke_agent(...)  # No token needed
```

---

### ❌ Mistake 2: Using IAM for AgentCore Gateway
```python
# WRONG - Trying to use IAM for Gateway
import boto3
response = requests.post(gateway_url, ...)  # No auth!
```

**Fix:** Use OAuth token
```python
# CORRECT - OAuth token
token = get_oauth_token()
response = requests.post(
    gateway_url,
    headers={'Authorization': f'Bearer {token}'},
    json=request_data
)
```

---

### ❌ Mistake 3: Mixing IAM and OAuth in Same Call
```python
# WRONG - Confused about which to use
token = get_oauth_token()
bedrock = boto3.client('bedrock-agent-runtime')
# Then trying to use token somehow?
```

**Fix:** Know which service needs which auth
- AWS services → IAM (boto3)
- AgentCore Gateway → OAuth (requests with token)

---

### ❌ Mistake 4: Putting OAuth Credentials in IAM Role
```bash
# WRONG - Adding Cognito client_id to IAM policy
{
  "Effect": "Allow",
  "Action": "cognito-idp:*",
  "Resource": "*",
  "Condition": {
    "StringEquals": {"cognito:client_id": "..."}
  }
}
```

**Fix:** OAuth credentials go in Lambda environment variables, not IAM
```bash
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --environment Variables="{COGNITO_CLIENT_ID=...,TOKEN_URL=...}"
```

---

### ❌ Mistake 5: Not Understanding Resource-Based Policies
```python
# Confusion: "Lambda has IAM role, why do I need resource-based policy?"
```

**Explanation:**
- **Execution role** (IAM) - What Lambda can call
- **Resource-based policy** - Who can call Lambda

```bash
# Lambda execution role (IAM) - Lambda → Bedrock
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeAgent",
  "Resource": "*"
}

# Lambda resource-based policy - Bedrock → Lambda
aws lambda add-permission \
  --function-name bedrock-gateway-proxy \
  --principal bedrock.amazonaws.com \
  --action lambda:InvokeFunction
```

## Quick Reference Table

| From | To | Auth Type | How |
|------|----|-----------|----|
| React UI | API Gateway | None/Cognito User Pools | Public or user login |
| API Gateway | Web API Lambda | IAM | Lambda execution role |
| Web API Lambda | Bedrock Agent | IAM | Lambda execution role |
| Bedrock Agent | Action Group | IAM | Agent service role |
| Action Group | Security Lambda | IAM | Resource-based policy |
| Security Lambda | AgentCore Gateway | OAuth | Cognito client credentials |
| AgentCore Gateway | AWS Services | IAM | Gateway execution role |

## Code Examples

### Example 1: Web API Lambda (IAM)
```python
import boto3

def lambda_handler(event, context):
    # Uses Lambda execution role automatically
    bedrock = boto3.client('bedrock-agent-runtime')
    
    response = bedrock.invoke_agent(
        agentId='AGENT_ID',
        agentAliasId='ALIAS_ID',
        sessionId='session-123',
        inputText='Check security status'
    )
    
    return {'statusCode': 200, 'body': 'Success'}
```

**IAM Role Needed:**
```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeAgent",
  "Resource": "arn:aws:bedrock:*:*:agent/*"
}
```

---

### Example 2: Security Lambda (OAuth)
```python
import requests
import base64
import os

def lambda_handler(event, context):
    # Get OAuth token
    client_id = os.environ['COGNITO_CLIENT_ID']
    token_url = os.environ['TOKEN_URL']
    
    credentials = f"{client_id}:"
    encoded = base64.b64encode(credentials.encode()).decode()
    
    token_response = requests.post(
        token_url,
        headers={'Authorization': f'Basic {encoded}'},
        data='grant_type=client_credentials'
    )
    token = token_response.json()['access_token']
    
    # Call Gateway with token
    gateway_url = os.environ['GATEWAY_URL']
    response = requests.post(
        gateway_url,
        headers={'Authorization': f'Bearer {token}'},
        json={'method': 'tools/call', 'params': {...}}
    )
    
    return format_response(response.json())
```

**No IAM permissions needed for Gateway call** - OAuth token provides auth.

---

## Debugging Auth Issues

### If AWS Service Call Fails:
```bash
# Check Lambda execution role
aws lambda get-function-configuration \
  --function-name FUNCTION_NAME \
  | jq '.Role'

# Check role permissions
aws iam get-role-policy \
  --role-name ROLE_NAME \
  --policy-name POLICY_NAME
```

**Look for:** Action matching the service you're calling (e.g., `bedrock:InvokeAgent`)

---

### If AgentCore Gateway Call Fails:
```bash
# Test token request manually
curl -X POST "$TOKEN_URL" \
  -H "Authorization: Basic $(echo -n "$CLIENT_ID:" | base64)" \
  -d "grant_type=client_credentials"

# Decode token to check scopes
echo "$TOKEN" | cut -d. -f2 | base64 -d | jq .

# Test Gateway with token
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"tools/call",...}'
```

**Look for:** 
- Token request: 200 OK with access_token
- Token scopes: Match Gateway requirements
- Gateway call: 200 OK with results

---

## Decision Flowchart

```
Need to call something?
│
├─ Is it an AWS service? (S3, Lambda, Bedrock, etc.)
│  │
│  └─ YES → Use IAM
│     │
│     ├─ Calling FROM Lambda?
│     │  └─ Add permission to Lambda execution role
│     │
│     └─ Calling TO Lambda?
│        └─ Add resource-based policy to Lambda
│
└─ Is it AgentCore Gateway?
   │
   └─ YES → Use OAuth
      │
      ├─ Get token from Cognito
      ├─ Use token in Authorization header
      └─ Check token has required scopes
```

## Summary

**IAM = AWS services**
- Automatic with boto3
- Uses Lambda execution role
- No credentials in code

**OAuth = AgentCore Gateway**
- Manual token request
- Uses Cognito client credentials
- Token in Authorization header

**Don't mix them up!**

## Related Documentation

- [OAuth/Cognito Token Issues](./OAUTH-COGNITO-TOKEN-ISSUES.md)
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md)
- [Security Lambda Fixed Code](../templates/gateway-proxy-lambda-fixed.py)
