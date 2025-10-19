# OpenAPI Schema Failures - What Didn't Work

## The Problem

**OpenAPI schema approach NEVER worked reliably.**

You tried multiple times, different formats, different tools - kept failing.

## What You Tried (All Failed)

### Attempt 1: Manual OpenAPI Schema
**Approach:** Write OpenAPI 3.0.0 schema by hand
**Result:** ❌ Validation errors, format issues, agent didn't call tools

### Attempt 2: Schema Generator Tools
**Approach:** Use tools to generate OpenAPI schema
**Result:** ❌ Generated wrong format, missing required fields

### Attempt 3: Copy Examples from AWS Docs
**Approach:** Copy example schemas from AWS documentation
**Result:** ❌ Examples too simple, didn't match real use case

### Attempt 4: Bedrock Console Schema Editor
**Approach:** Use AWS Console's built-in schema editor
**Result:** ❌ Validation passed but agent still didn't work

### Attempt 5: Function Details Instead of OpenAPI
**Approach:** Use Bedrock Agent "function details" instead of OpenAPI schema
**Result:** ❌ Limited functionality, still had issues

## Why OpenAPI Schema Kept Failing

### Issue 1: Version Confusion
- OpenAPI 3.0.0 required (not 3.0.1, 3.0.2, or 3.1.0)
- Easy to get wrong version
- No clear error messages

### Issue 2: operationId Requirements
- Must be unique across all operations
- Must be alphanumeric with only hyphens/underscores
- Agent uses this to map to Lambda function
- If wrong, agent can't invoke

### Issue 3: Description Field Critical But Unclear
- Agent uses `description` to decide when to call tool
- Documentation doesn't emphasize this enough
- Vague descriptions = agent doesn't call tool

### Issue 4: Parameter Format Strict
- Parameters must be in specific format
- `requestBody` vs `parameters` confusion
- Type definitions must be exact

### Issue 5: Response Format Requirements
- Must define response schema
- Agent uses this for orchestration
- Missing response = agent confused

### Issue 6: Validation Passes But Doesn't Work
- Schema validates successfully
- Agent prepares successfully
- But agent still doesn't call tools
- No clear error message why

## The Workaround You Tried

### Workaround 1: Bypass Action Groups Entirely
**Approach:** 
- Skip Bedrock Agent action groups
- Call AgentCore Gateway directly from Web API Lambda
- No OpenAPI schema needed

**Code:**
```python
def lambda_handler(event, context):
    user_input = event['body']['inputText']
    
    # Parse user input manually
    if 'security status' in user_input.lower():
        tool_name = 'SecurityMCPTools___CheckSecurityServices'
        params = {'region': 'us-east-1'}
    elif 'findings' in user_input.lower():
        tool_name = 'SecurityMCPTools___GetSecurityFindings'
        params = {'region': 'us-east-1', 'service': 'securityhub'}
    
    # Call Gateway directly
    response = call_gateway(tool_name, params)
    return format_response(response)
```

**Result:** ❌ 
- Lost Bedrock Agent orchestration
- Manual parsing too brittle
- No multi-turn conversation
- No parameter extraction

### Workaround 2: Single Generic Action
**Approach:**
- Create one action group with generic "execute" operation
- Pass all parameters as JSON string
- Lambda parses and routes

**OpenAPI:**
```json
{
  "paths": {
    "/execute": {
      "post": {
        "description": "Execute any security operation",
        "parameters": [{
          "name": "operation",
          "description": "Operation to execute"
        }, {
          "name": "params",
          "description": "JSON string of parameters"
        }]
      }
    }
  }
}
```

**Result:** ❌
- Agent couldn't extract structured parameters
- JSON string parsing failed
- Lost type safety

### Workaround 3: Multiple Simple Actions
**Approach:**
- Create separate action group for each operation
- Each with minimal schema
- Hope agent figures it out

**Result:** ❌
- Too many action groups
- Agent confused which to call
- Management nightmare

## What Actually Works

### Solution 1: Use Bedrock Agent Function Details (Not OpenAPI)

**Instead of OpenAPI schema, use function details:**

```bash
aws bedrock-agent create-agent-action-group \
  --agent-id AGENT_ID \
  --action-group-name SecurityActions \
  --action-group-executor lambda=arn:aws:lambda:...:function:SecurityLambda \
  --function-schema '{
    "functions": [
      {
        "name": "checkSecurityStatus",
        "description": "Check status of AWS security services. Use when user asks about enabled services, security service status, or wants to know if GuardDuty, Security Hub, Inspector are running.",
        "parameters": {
          "region": {
            "type": "string",
            "description": "AWS region (us-east-1, us-west-2, etc.)",
            "required": false
          },
          "service": {
            "type": "string",
            "description": "Specific service to check (guardduty, securityhub, inspector)",
            "required": false
          }
        }
      }
    ]
  }'
```

**Pros:**
- Simpler format than OpenAPI
- Better error messages
- Agent understands better

**Cons:**
- Less flexible than OpenAPI
- Limited to simple parameter types

### Solution 2: Minimal OpenAPI + Detailed Agent Instructions

**Use minimal OpenAPI schema:**
```json
{
  "openapi": "3.0.0",
  "info": {"title": "Security API", "version": "1.0.0"},
  "paths": {
    "/check-security": {
      "post": {
        "operationId": "checkSecurity",
        "description": "Check AWS security. Use for ANY security-related question.",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "query": {"type": "string", "description": "User's security question"}
                }
              }
            }
          }
        },
        "responses": {"200": {"description": "Success"}}
      }
    }
  }
}
```

**Then rely on detailed agent instructions:**
```
When user asks about security:
1. ALWAYS call the checkSecurity action
2. Pass the user's question as the 'query' parameter
3. Let the Lambda function parse and route the request
```

**Lambda does the heavy lifting:**
```python
def lambda_handler(event, context):
    query = extract_query(event)
    
    # Parse query and determine tool
    if 'status' in query or 'enabled' in query:
        tool = 'CheckSecurityServices'
        params = extract_params_for_status(query)
    elif 'findings' in query or 'vulnerabilities' in query:
        tool = 'GetSecurityFindings'
        params = extract_params_for_findings(query)
    
    # Call Gateway
    return call_gateway(tool, params)
```

**Pros:**
- Simple OpenAPI schema (less to break)
- Agent always calls action (one clear trigger)
- Lambda has full control over routing

**Cons:**
- Lambda more complex
- Lose some Bedrock Agent orchestration benefits

### Solution 3: Use AgentCore CLI to Generate Schema

**Let AgentCore generate the schema:**

```bash
# If you have AgentCore MCP server running
agentcore generate-schema \
  --server-path /path/to/mcp/server \
  --output action-group-schema.json
```

**This generates Bedrock-compatible schema from MCP server tools.**

**Pros:**
- Automatically correct format
- Matches actual tool signatures
- No manual schema writing

**Cons:**
- Requires AgentCore CLI working (which was unreliable for you)
- Still need to test agent behavior

## Recommended Approach

Based on your experience, here's what to do:

### Step 1: Start with Function Details (Not OpenAPI)

Use function details format - it's simpler and more reliable:

```python
function_schema = {
    "functions": [
        {
            "name": "checkSecurityStatus",
            "description": "Check AWS security service status. Use when user asks: 'check security', 'is GuardDuty enabled', 'security services status'.",
            "parameters": {
                "region": {
                    "type": "string",
                    "description": "AWS region. Default: us-east-1",
                    "required": False
                }
            }
        }
    ]
}
```

### Step 2: If Function Details Don't Work, Use Minimal OpenAPI

Create the simplest possible OpenAPI schema:

```json
{
  "openapi": "3.0.0",
  "info": {"title": "Security", "version": "1.0.0"},
  "paths": {
    "/security": {
      "post": {
        "operationId": "handleSecurity",
        "description": "Handle all security requests",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "request": {"type": "string"}
                }
              }
            }
          }
        },
        "responses": {"200": {"description": "OK"}}
      }
    }
  }
}
```

### Step 3: Move Complexity to Lambda

Let Lambda do the parsing and routing:

```python
def lambda_handler(event, context):
    # Extract user input
    user_input = event.get('inputText', '')
    parameters = event.get('parameters', [])
    
    # Parse and route
    operation, params = parse_user_request(user_input, parameters)
    
    # Map to Gateway tool
    tool_name, gateway_params = map_to_gateway_tool(operation, params)
    
    # Call Gateway
    result = call_gateway(tool_name, gateway_params)
    
    return format_response(event, result)
```

## Testing Checklist

When trying any approach:

- [ ] Schema validates (if using OpenAPI)
- [ ] Agent prepares successfully
- [ ] Agent status is PREPARED
- [ ] Test with simple query: "check security"
- [ ] Enable agent tracing to see what happens
- [ ] Check Lambda is invoked (CloudWatch logs)
- [ ] Check Lambda receives correct event format
- [ ] Check Lambda can call Gateway
- [ ] Check Gateway returns results
- [ ] Check agent returns results to user

**If any step fails, that's where the problem is.**

## Key Lessons

1. **OpenAPI schema is fragile** - Small mistakes break everything
2. **Validation passing ≠ working** - Schema can validate but agent still fails
3. **Simpler is better** - Minimal schema + smart Lambda > complex schema
4. **Function details more reliable** - Use instead of OpenAPI when possible
5. **Test incrementally** - Don't build full schema before testing
6. **Agent tracing essential** - Only way to see what agent is thinking

## Related Files

- [Security Action Group Schema](../templates/security-action-group-schema.json) - Complete OpenAPI (if you want to try again)
- [Agent Tool Selection](./AGENT-TOOL-SELECTION-ISSUE.md) - How agent decides to call tools
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md) - Master issues list
