# Complete Issues & Solutions Reference

## Master List of All Issues You Faced

### LAYER 4: BEDROCK AGENT ISSUES

#### Issue 1: Agent Not Reaching PREPARED State
**Symptom:** Agent stuck in PREPARING or NOT_PREPARED state
**Root Cause:** 
- Missing required configuration (role, model, instructions)
- Action group not properly configured
- Not running `prepare-agent` after changes

**Solution:**
```bash
# After any agent changes
aws bedrock-agent prepare-agent --agent-id AGENT_ID

# Wait for PREPARED state
python3 scripts/wait-for-agent-ready.py AGENT_ID SecurityLambda
```

**Prevention:** Always run prepare-agent after create/update

---

#### Issue 2: Multiple Agents/Versions/Aliases Confusion
**Symptom:** Lost track of which agent ID, version, alias to use
**Root Cause:** Multiple agents, versions, aliases with no tracking system

**Solution:**
```bash
# Get inventory of all agents
python3 scripts/bedrock-agent-inventory.py

# Check current active configuration
./scripts/which-agent.sh

# Update state file after changes
vim templates/agent-state.json
```

**Prevention:** Maintain `agent-state.json` as single source of truth

---

#### Issue 3: Testing Before Agent Ready/Stable
**Symptom:** Tests fail immediately after agent creation/update
**Root Cause:** 
- Agent not in PREPARED state
- AWS internal routing not stabilized (10-15s lag)

**Solution:**
```bash
# Run pre-test checklist
./scripts/pre-test-checklist.sh AGENT_ID SecurityLambda

# Wait for ready + stabilization
python3 scripts/wait-for-agent-ready.py AGENT_ID SecurityLambda
sleep 15  # Stabilization wait
```

**Prevention:** Always wait 30-60s after prepare-agent before testing

---

### LAYER 5: ACTION GROUP ISSUES

#### Issue 4: OpenAPI Schema Format Errors
**Symptom:** Action group creation fails with validation errors
**Root Cause:**
- Wrong OpenAPI version (must be 3.0.0, not 3.1.0)
- Missing `operationId` in operations
- Invalid schema structure

**Solution:**
```bash
# Validate schema before deployment
python3 scripts/validate-openapi-schema.py schema.json
```

**Required Format:**
```json
{
  "openapi": "3.0.0",
  "info": {"title": "...", "version": "1.0.0"},
  "paths": {
    "/action": {
      "post": {
        "operationId": "actionName",
        "description": "...",
        "requestBody": {...},
        "responses": {...}
      }
    }
  }
}
```

**Prevention:** Use template `templates/bedrock-action-group-schema-template.json`

---

#### Issue 5: Action Group Target Not Set
**Symptom:** DependencyFailedException when agent invokes action
**Root Cause:** Action group has no Lambda target or wrong Lambda ARN

**Solution:**
```bash
# Set target when creating action group
aws bedrock-agent create-agent-action-group \
  --agent-id AGENT_ID \
  --action-group-name SecurityActions \
  --action-group-executor lambda=arn:aws:lambda:region:account:function:bedrock-gateway-proxy \
  --api-schema file://schema.json

# Verify target
aws bedrock-agent get-agent-action-group \
  --agent-id AGENT_ID \
  --agent-version DRAFT \
  --action-group-id ACTION_GROUP_ID \
  | jq '.agentActionGroup.actionGroupExecutor.lambda'
```

**Prevention:** Always specify `--action-group-executor` with correct Lambda ARN

---

### LAYER 6: TARGET LAMBDA ISSUES

#### Issue 6: Missing Lambda Resource-Based Policy
**Symptom:** DependencyFailedException - Lambda never executes
**Root Cause:** Lambda doesn't have permission for bedrock.amazonaws.com to invoke it

**Solution:**
```bash
# Add permission
aws lambda add-permission \
  --function-name bedrock-gateway-proxy \
  --statement-id bedrock-agent-invoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:region:account:agent/AGENT_ID" \
  --source-account ACCOUNT_ID

# Verify
aws lambda get-policy --function-name bedrock-gateway-proxy | jq '.Policy | fromjson'
```

**Prevention:** Add permission immediately after creating Lambda

---

#### Issue 7: Wrong Lambda Response Format
**Symptom:** Lambda executes but agent fails with DependencyFailedException
**Root Cause:** Response missing `messageVersion` or `response` wrapper, or `body` is dict not string

**Current Code (WRONG):**
```python
return {
    'actionGroup': event['actionGroup'],
    'apiPath': event['apiPath'],
    'httpMethod': event['httpMethod'],
    'httpStatusCode': 200,
    'responseBody': {
        'application/json': {
            'body': {'data': 'value'}  # WRONG: dict not string
        }
    }
}
```

**Fixed Code:**
```python
return {
    'messageVersion': '1.0',  # REQUIRED
    'response': {  # REQUIRED wrapper
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 200,
        'responseBody': {
            'application/json': {
                'body': json.dumps({'data': 'value'})  # MUST be string
            }
        }
    }
}
```

**Solution:**
```bash
# Validate response format
python3 scripts/validate-action-group-response.py test-response.json
```

**Prevention:** Use helper functions from `templates/gateway-proxy-lambda-fixed.py`

---

#### Issue 8: Lambda Timeout
**Symptom:** Logs show "Task timed out after 3.00 seconds"
**Root Cause:** Default Lambda timeout (3s) too short for Gateway calls

**Solution:**
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --timeout 30
```

**Prevention:** Set timeout to 30+ seconds for all action group Lambdas

---

#### Issue 9: Hardcoded Credentials in Lambda
**Symptom:** Code has hardcoded URLs, client IDs
**Root Cause:** Not using environment variables

**Solution:**
```python
# Use environment variables
gateway_url = os.environ.get('GATEWAY_URL')
client_id = os.environ.get('COGNITO_CLIENT_ID')
```

**Set in Lambda:**
```bash
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --environment Variables="{GATEWAY_URL=https://...,COGNITO_CLIENT_ID=...}"
```

**Prevention:** Never hardcode credentials, always use environment variables

---

#### Issue 10: No Input Validation
**Symptom:** Lambda crashes with KeyError when event missing fields
**Root Cause:** Accessing event fields without checking existence

**Solution:**
```python
# Validate before accessing
if 'actionGroup' not in event:
    return error_response(event, 'Missing actionGroup')

# Use .get() with defaults
operation = event.get('actionGroup', '')
parameters = event.get('parameters', [])
```

**Prevention:** Always validate event structure at start of handler

---

### TROUBLESHOOTING ISSUES

#### Issue 11: Checking Logs Too Early
**Symptom:** No logs appear, think Lambda didn't execute
**Root Cause:** CloudWatch logs have 5-30s lag after invocation

**Solution:**
```bash
# Wait 30s after test, then check logs
sleep 30
./scripts/monitor-agent-logs.sh bedrock-gateway-proxy 5
```

**Prevention:** Always wait 30s before checking logs

---

#### Issue 12: Lost in Troubleshooting
**Symptom:** Don't know where to start debugging
**Root Cause:** No systematic troubleshooting workflow

**Solution:** Follow this order:
1. Check agent status (PREPARED?)
2. Check action group state (ENABLED?)
3. Check Lambda permission (bedrock.amazonaws.com?)
4. Test Lambda directly with sample event
5. Check CloudWatch logs (wait 30s first)
6. Validate Lambda response format

**Prevention:** Use `scripts/pre-test-checklist.sh` before every test

---

### DEPLOYMENT ISSUES

#### Issue 13: Forgot Which Bucket to Deploy To
**Symptom:** Built React app but deployed to wrong S3 bucket
**Root Cause:** Multiple S3 buckets, no clear tracking

**Solution:**
```bash
# Use interactive deployment script
./scripts/deploy-frontend.sh

# Script shows bucket name and asks for confirmation
```

**Prevention:** Use deployment scripts, never manual `aws s3 sync`

---

#### Issue 14: Build vs Deploy Disconnect
**Symptom:** Built code but forgot to deploy, or vice versa
**Root Cause:** Separate build and deploy steps

**Solution:**
```bash
# Combined build + deploy script
cd react-app
npm run build
aws s3 sync build/ s3://BUCKET_NAME --delete
```

**Prevention:** Single script that does both build and deploy

---

---

### OAUTH & COGNITO ISSUES

#### Issue 15: Token Getting Expired
**Symptom:** Lambda works first time, then fails with 401 Unauthorized
**Root Cause:** Token cached but expired (default 1 hour)

**Solution:** Get fresh token on every invocation (current code is correct)
```python
def lambda_handler(event, context):
    # Get fresh token every time - CORRECT
    token = get_oauth_token()
```

**Prevention:** Don't cache tokens unless you check expiration

---

#### Issue 16: OAuth Token Request Failing
**Symptom:** `Failed to get OAuth token: 400` or `401`
**Root Causes:**
- Wrong client credentials
- Wrong token URL
- Client not configured for client_credentials flow
- Wrong OAuth scopes

**Solution:**
```bash
# Verify client configuration
aws cognito-idp describe-user-pool-client \
  --user-pool-id POOL_ID \
  --client-id CLIENT_ID

# Check AllowedOAuthFlows includes "client_credentials"
# Check AllowedOAuthScopes matches Gateway requirements
```

**Prevention:** Test token request manually with curl before deploying

---

#### Issue 17: Lambda in VPC Can't Reach Cognito
**Symptom:** Token request times out
**Root Cause:** Lambda in VPC without NAT Gateway

**Solution:**
```bash
# Remove Lambda from VPC if not needed
aws lambda update-function-configuration \
  --function-name bedrock-gateway-proxy \
  --vpc-config SubnetIds=[],SecurityGroupIds=[]
```

**Prevention:** Only put Lambda in VPC if it needs to access VPC resources

---

#### Issue 18: IAM vs OAuth Confusion
**Symptom:** Kept switching between IAM and OAuth, repeated failures
**Root Cause:** Not understanding when to use which authentication method

**Simple Rule:**
- **AWS services** (S3, Bedrock, Lambda) → Use IAM (boto3 automatic)
- **AgentCore Gateway** → Use OAuth (Cognito token)

**Solution:** See [IAM vs OAuth Decision Guide](./IAM-VS-OAUTH-DECISION.md)

**Prevention:** 
- IAM = boto3 calls (no credentials in code)
- OAuth = requests calls (need token in header)

---

### AGENTCORE GATEWAY ISSUES

#### Issue 19: Multiple Gateway Versions/Aliases Confusion
**Symptom:** Multiple Gateway URLs, not sure which one to use
**Root Cause:** AgentCore creates versions and aliases, lost track

**Solution:** Track in `agent-state.json`
```json
{
  "agentcore_gateway": {
    "active_url": "https://...",
    "version": "1",
    "alias": "prod"
  }
}
```

**Prevention:** Maintain single source of truth for Gateway URL

---

#### Issue 20: Gateway Not Ready After Deployment
**Symptom:** Gateway returns 503 Service Unavailable
**Root Cause:** Gateway takes 30-60s to become ready

**Solution:**
```bash
agentcore gateway wait --gateway-id GATEWAY_ID --status READY
sleep 15  # Stabilization
```

**Prevention:** Always wait for READY + 15s before testing

---

#### Issue 21: Wrong Gateway URL in Lambda
**Symptom:** Lambda gets 404 or connection refused
**Root Cause:** Hardcoded old Gateway URL

**Solution:** Use environment variable
```python
gateway_url = os.environ.get('GATEWAY_URL')
```

**Prevention:** Never hardcode Gateway URL

---

### PARAMETER MAPPING ISSUES (BIGGEST PROBLEM)

#### Issue 22: Parameters Not Getting Passed
**Symptom:** Gateway receives empty or null parameters
**Root Cause:** Hardcoded parameter extraction - only handles 3 specific parameters

**Current code:**
```python
if param_name == 'region':
    mcp_params['region'] = param_value
# Other parameters? LOST!
```

**Solution:** Use parameter mapping table (see `templates/parameter-mapper.py`)

**Prevention:** Define all parameter mappings upfront

---

#### Issue 23: Default Values Not Applied
**Symptom:** Tool fails with "missing required parameter"
**Root Cause:** No defaults when user doesn't specify parameter

**Solution:** Start with defaults, override with provided values
```python
mcp_params = TOOL_DEFAULTS[tool_name].copy()
# Then add provided parameters
```

**Prevention:** Define defaults for all optional parameters

---

#### Issue 24: Wrong Parameter Names
**Symptom:** Gateway rejects - unknown parameter
**Root Cause:** Bedrock names don't match Gateway names

**Examples:**
- `service` → `service_names` (singular to plural)
- `serviceType` → `service_type` (camelCase to snake_case)

**Solution:** Maintain name mapping table per tool

**Prevention:** Document all parameter name mappings

---

#### Issue 25: Type Conversion Issues
**Symptom:** Gateway rejects - wrong type
**Root Cause:** Bedrock sends strings, Gateway expects specific types

**Examples:**
- `"50"` (string) → `50` (integer)
- `"EC2"` (string) → `["EC2"]` (array)

**Solution:** Convert based on tool signature
```python
if param_type == 'integer':
    value = int(value)
elif param_type == 'array':
    value = [value]
```

**Prevention:** Define type for each parameter in tool signature

---

#### Issue 26: Wrong Tool Mapping
**Symptom:** Gateway says tool not found
**Root Cause:** Operation ID doesn't match Gateway tool name

**Example:**
- OpenAPI: `checkSecurityStatus`
- Gateway: `SecurityMCPTools___CheckSecurityServices`

**Solution:** Explicit operation-to-tool mapping table

**Prevention:** Test all operation mappings

---

### AGENT TOOL SELECTION ISSUES (BIGGEST ISSUE)

#### Issue 27: Agent Returns Generic Response Instead of Calling Tool
**Symptom:** Agent says "I can help with security" instead of calling action group
**Root Cause:** OpenAPI schema `description` field doesn't tell agent WHEN to call tool

**The agent uses the `description` field to decide when to invoke an operation!**

**Wrong:**
```json
{"description": "Check security"}
```

**Correct:**
```json
{"description": "Use this operation when the user asks about security service status, enabled services, or wants to check if security services like GuardDuty are enabled. Examples: 'check security status', 'are security services enabled', 'what security services are running'."}
```

**Solution:** Write detailed descriptions with:
- "Use this operation when..."
- Multiple example user phrases
- Clear distinction from other operations

**Prevention:** Test with natural language, enable agent tracing

---

#### Issue 28: Agent Extracts Wrong Parameter Values
**Symptom:** User says "Virginia" but agent sends region="Virginia" instead of "us-east-1"
**Root Cause:** Parameter description doesn't include mapping guidance

**Wrong:**
```json
{"name": "region", "description": "AWS region"}
```

**Correct:**
```json
{"name": "region", "description": "AWS region to check (e.g., us-east-1, us-west-2). If user mentions 'Virginia', map to 'us-east-1'. If not specified, use 'us-east-1'."}
```

**Solution:** Include mapping rules in parameter descriptions

**Prevention:** Test with region names, service aliases, etc.

---

#### Issue 29: Agent Instructions Too Generic
**Symptom:** Agent doesn't know it should use action groups
**Root Cause:** Instructions don't mention action group capabilities

**Wrong:**
```
You are a helpful assistant.
```

**Correct:**
```
You are an AWS security chatbot. You have action groups to check security services, get findings, check encryption, and analyze network security. ALWAYS use action groups to get real-time AWS data instead of providing generic advice.
```

**Solution:** Explicitly list capabilities and instruct to use action groups

**Prevention:** Include "ALWAYS use action groups" in instructions

---

### OPENAPI SCHEMA ISSUES (NEVER WORKED RELIABLY)

#### Issue 30: OpenAPI Schema Validation Passes But Agent Doesn't Work
**Symptom:** Schema validates, agent prepares, but agent doesn't call tools
**Root Cause:** Schema format correct but descriptions inadequate for agent

**Solution:** Use **Function Details** instead of OpenAPI
```bash
aws bedrock-agent create-agent-action-group \
  --function-schema '{
    "functions": [{
      "name": "checkSecurity",
      "description": "Check security. Use when user asks: check security, is GuardDuty enabled",
      "parameters": {"region": {"type": "string", "required": false}}
    }]
  }'
```

**Prevention:** Start with function details, only use OpenAPI if needed

---

#### Issue 31: OpenAPI Schema Too Complex, Kept Breaking
**Symptom:** Multiple operations, complex parameters, constant validation errors
**Root Cause:** OpenAPI schema fragile, small mistakes break everything

**Solution:** Use minimal OpenAPI + smart Lambda
```json
{
  "paths": {
    "/security": {
      "post": {
        "operationId": "handleSecurity",
        "description": "Handle all security requests",
        "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}}
      }
    }
  }
}
```

Let Lambda parse and route requests.

**Prevention:** Keep schema minimal, move complexity to Lambda

---

### GATEWAY DEPLOYMENT FAILURES (CRITICAL)

#### Issue 32: Gateway Needs HTTP Endpoint, Not ARN
**Symptom:** Gateway creation fails with "Invalid target_source"
**Root Cause:** Gave Lambda ARN instead of HTTP endpoint

**What you tried (WRONG):**
```python
target_source="arn:aws:lambda:..."  # ❌ ARN doesn't work
```

**Solution:** Deploy MCP server to AgentCore Runtime first, get HTTP endpoint
```bash
agentcore launch  # Returns HTTP endpoint
# Use: http://runtime-abc123.agentcore.us-east-1.amazonaws.com/invocations
```

**Prevention:** Always deploy to Runtime first, then create Gateway with Runtime endpoint

---

#### Issue 33: Didn't Know Which Version/Alias to Attach
**Symptom:** Confused about Gateway versions, Runtime versions, Agent versions
**Root Cause:** Misunderstanding - no manual version attachment needed

**The Truth:**
- Gateway manages its own versions automatically
- Runtime endpoint URL includes version
- No manual attachment needed

**Solution:** Just use the HTTP endpoint URL - version is embedded

**Prevention:** Don't try to manually manage versions

---

#### Issue 34: Wrong Client ID (Used Pool ID)
**Symptom:** OAuth fails with 400 Bad Request
**Root Cause:** Used Cognito User Pool ID instead of Client ID

**Wrong:**
```python
client_id = "us-east-1_XXXXXXXXX"  # ❌ This is pool ID
```

**Correct:**
```bash
# Get client ID
aws cognito-idp list-user-pool-clients --user-pool-id POOL_ID
# Use: 6aarhftf6bopppar05humcp2r6
```

**Prevention:** Client ID is alphanumeric, Pool ID has underscore

---

#### Issue 35: Token Endpoint Wrong Format
**Symptom:** Token request fails with connection error
**Root Cause:** Used wrong Cognito endpoint format

**Wrong:**
```python
token_url = "https://cognito-idp.us-east-1.amazonaws.com/..."  # ❌
```

**Correct:**
```python
token_url = "https://YOUR-DOMAIN.auth.us-east-1.amazoncognito.com/oauth2/token"  # ✅
```

**Prevention:** Use OAuth endpoint, not Cognito IDP endpoint

---

## Quick Reference: Tools for Each Issue

| Issue | Tool | Command |
|-------|------|---------|
| Agent not ready | wait-for-agent-ready.py | `python3 scripts/wait-for-agent-ready.py AGENT_ID Lambda` |
| Multiple agents confusion | bedrock-agent-inventory.py | `python3 scripts/bedrock-agent-inventory.py` |
| Which agent to use | which-agent.sh | `./scripts/which-agent.sh` |
| OpenAPI schema errors | validate-openapi-schema.py | `python3 scripts/validate-openapi-schema.py schema.json` |
| Lambda response errors | validate-action-group-response.py | `python3 scripts/validate-action-group-response.py response.json` |
| Pre-test validation | pre-test-checklist.sh | `./scripts/pre-test-checklist.sh AGENT_ID Lambda` |
| Log monitoring | monitor-agent-logs.sh | `./scripts/monitor-agent-logs.sh Lambda 5` |
| DependencyFailedException | fix-dependency-failed.sh | `./fix-dependency-failed.sh AGENT_ID Lambda` |

## Critical Workflows

### After Creating Agent
```bash
# 1. Create agent
aws bedrock-agent create-agent ...

# 2. Create action group with target
aws bedrock-agent create-agent-action-group \
  --action-group-executor lambda=arn:aws:lambda:...:function:bedrock-gateway-proxy \
  ...

# 3. Add Lambda permission
aws lambda add-permission \
  --function-name bedrock-gateway-proxy \
  --principal bedrock.amazonaws.com \
  ...

# 4. Prepare agent
aws bedrock-agent prepare-agent --agent-id AGENT_ID

# 5. Wait for ready
python3 scripts/wait-for-agent-ready.py AGENT_ID bedrock-gateway-proxy

# 6. Stabilization wait
sleep 15

# 7. Test
```

### Before Every Test
```bash
# 1. Pre-test checklist
./scripts/pre-test-checklist.sh AGENT_ID bedrock-gateway-proxy

# 2. If passes, test
# 3. If fails, fix issues first
```

### When Test Fails
```bash
# 1. Wait 30s for logs
sleep 30

# 2. Check logs
./scripts/monitor-agent-logs.sh bedrock-gateway-proxy 5

# 3. Check agent status
aws bedrock-agent get-agent --agent-id AGENT_ID | jq '.agent.agentStatus'

# 4. Check Lambda permission
aws lambda get-policy --function-name bedrock-gateway-proxy

# 5. Test Lambda directly
aws lambda invoke --function-name bedrock-gateway-proxy --payload file://test-event.json response.json

# 6. Validate response
python3 scripts/validate-action-group-response.py response.json
```

## Files to Fix

### Priority 1: MUST FIX
1. **gateway_proxy_lambda_working.py** - Wrong response format (missing messageVersion, response wrapper)
2. **Lambda permissions** - Add resource-based policy for bedrock.amazonaws.com
3. **Lambda timeout** - Increase to 30+ seconds
4. **Lambda environment variables** - Move hardcoded values to env vars

### Priority 2: SHOULD FIX
1. **agent-state.json** - Create and maintain for tracking
2. **OpenAPI schema** - Validate with script before deployment
3. **Deployment scripts** - Use interactive scripts instead of manual commands

### Priority 3: NICE TO HAVE
1. **Error handling** - Add comprehensive try/catch in Lambda
2. **Logging** - Add structured logging with context
3. **Monitoring** - Set up CloudWatch alarms for failures

## Templates to Use

| Template | Purpose | Location |
|----------|---------|----------|
| gateway-proxy-lambda-fixed.py | Fixed Lambda with correct response format | templates/ |
| action-group-lambda-response.py | Response format reference | templates/ |
| bedrock-action-group-schema-template.json | Valid OpenAPI schema | templates/ |
| agent-state.json | Agent tracking | templates/ |

## Documentation References

| Topic | Document |
|-------|----------|
| DependencyFailedException | wikis/BEDROCK-AGENT-DEPENDENCY-FAILED-EXCEPTION.md |
| Troubleshooting workflow | wikis/AGENT-TROUBLESHOOTING-WORKFLOW.md |
| S3 Frontend deployment | wikis/01-S3-FRONTEND-COMPLETE.md |
| Web API Lambda | wikis/03-WEB-API-LAMBDA-COMPLETE.md |
| Architecture overview | wikis/00-ARCHITECTURE-OVERVIEW.md |

## Next Steps

1. **Fix gateway_proxy_lambda_working.py** - Use fixed version from templates/
2. **Add Lambda permission** - Run fix-dependency-failed.sh
3. **Test with checklist** - Run pre-test-checklist.sh before testing
4. **Create agent-state.json** - Track active configuration
5. **Document your specific agent IDs** - Update templates with real values
