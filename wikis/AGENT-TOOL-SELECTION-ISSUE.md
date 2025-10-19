# Agent Tool Selection - The Biggest Issue

## The Problem

**Symptom:** Agent returns generic response instead of calling action group tool
**Root Cause:** Agent doesn't know WHEN to call which tool

```
User: "Check security status for EC2"
  ↓
Agent: "I can help you with security. What would you like to know?" ❌ GENERIC RESPONSE
  
Instead of:
  ↓
Agent: Calls checkSecurityStatus with {region: "us-east-1", service: "guardduty"} ✅
```

## How Agent Decides to Call Tools

The agent uses **THREE sources** to decide when to call a tool:

### 1. Agent Instructions (General Guidance)
Located in: Agent configuration
```
You are a security chatbot that helps users check AWS security status.
You can check security services, get findings, check encryption, and analyze network security.
```

### 2. OpenAPI Schema `description` Field (CRITICAL)
Located in: Action group OpenAPI schema

**This is where tool selection happens!**

The `description` field tells the agent:
- WHEN to call this operation
- WHAT user requests trigger this operation
- EXAMPLES of user phrases

```json
{
  "paths": {
    "/check-security-status": {
      "post": {
        "description": "Use this operation when the user asks about security service status, enabled services, or wants to check if security services like GuardDuty, Security Hub, Inspector are enabled. Examples: 'check security status', 'are security services enabled', 'what security services are running'."
      }
    }
  }
}
```

### 3. Parameter `description` Fields (Parameter Extraction)
Located in: OpenAPI schema parameters

Tells agent HOW to extract parameter values from user input:

```json
{
  "parameters": [{
    "name": "region",
    "description": "AWS region to check (e.g., us-east-1, us-west-2). If user mentions 'Virginia', map to 'us-east-1'. If not specified, use 'us-east-1'."
  }]
}
```

## Common Mistakes

### ❌ Mistake 1: Vague Operation Description
```json
{
  "description": "Check security status"
}
```

**Problem:** Agent doesn't know when to use this vs other operations

**Fix:** Be specific with examples
```json
{
  "description": "Use this operation when the user asks about security service status, enabled services, or wants to check if security services like GuardDuty, Security Hub, Inspector, Access Analyzer, Trusted Advisor, or Macie are enabled in a region. Examples: 'check security status', 'are security services enabled', 'what security services are running', 'check GuardDuty status'."
}
```

---

### ❌ Mistake 2: Missing Parameter Mapping Guidance
```json
{
  "name": "region",
  "description": "AWS region"
}
```

**Problem:** Agent doesn't know how to extract region from "Virginia" or "California"

**Fix:** Provide mapping guidance
```json
{
  "name": "region",
  "description": "AWS region to check (e.g., us-east-1, us-west-2). If user mentions a region name like 'Virginia', map to 'us-east-1'. If user says 'California', map to 'us-west-1'. If not specified, use 'us-east-1'."
}
```

---

### ❌ Mistake 3: Overlapping Operation Descriptions
```json
{
  "/check-security": {
    "description": "Check security"
  },
  "/get-security-info": {
    "description": "Get security information"
  }
}
```

**Problem:** Agent confused which one to call

**Fix:** Make descriptions distinct
```json
{
  "/check-security-status": {
    "description": "Use when user asks about security SERVICE STATUS (enabled/disabled). Examples: 'is GuardDuty enabled', 'check security services'."
  },
  "/get-security-findings": {
    "description": "Use when user asks about security FINDINGS/ISSUES/VULNERABILITIES. Examples: 'show me findings', 'what security issues', 'get vulnerabilities'."
  }
}
```

---

### ❌ Mistake 4: No Examples in Description
```json
{
  "description": "Use this to check security services"
}
```

**Problem:** Agent doesn't know what user phrases trigger this

**Fix:** Add multiple examples
```json
{
  "description": "Use this operation when the user asks about security service status. Examples: 'check security status', 'are security services enabled', 'what security services are running', 'check GuardDuty status', 'is Security Hub active'."
}
```

---

### ❌ Mistake 5: Agent Instructions Too Generic
```
You are a helpful assistant.
```

**Problem:** Agent doesn't know it should use action groups

**Fix:** Be specific about capabilities
```
You are a security chatbot that helps users check AWS security status.

You have access to the following capabilities through action groups:
1. Check security service status (GuardDuty, Security Hub, Inspector, etc.)
2. Get security findings and vulnerabilities
3. Check storage encryption (S3, EBS, RDS, etc.)
4. Check network security (ELB, VPC, API Gateway, CloudFront)

When a user asks about security, use the appropriate action group to get real-time information from AWS.
Always call the action group instead of providing generic security advice.
```

---

## Complete Solution

### Step 1: Write Detailed Agent Instructions

```
You are an AWS security chatbot that helps users check their AWS security posture.

Your capabilities:
- Check if security services (GuardDuty, Security Hub, Inspector, Access Analyzer, Trusted Advisor, Macie) are enabled
- Retrieve security findings and vulnerabilities from these services
- Check encryption status of storage resources (S3, EBS, RDS, DynamoDB, EFS, ElastiCache)
- Analyze network security configuration (ELB, VPC, API Gateway, CloudFront)

Important guidelines:
1. ALWAYS use action groups to get real-time data from AWS
2. DO NOT provide generic security advice without checking actual AWS resources
3. When user asks about security, determine which action group operation to call
4. Extract parameters from user input (region, service, severity, etc.)
5. If user mentions region names like "Virginia", map to AWS region codes like "us-east-1"
6. If parameters are missing, use defaults: region=us-east-1, check all services

Parameter extraction rules:
- Region: Use AWS region codes (us-east-1, us-west-2, eu-west-1, etc.)
  - "Virginia" → "us-east-1"
  - "California" → "us-west-1"  
  - "Ireland" → "eu-west-1"
- Services: Use lowercase (guardduty, securityhub, inspector, s3, ebs, rds, etc.)
- Severity: Use CRITICAL, HIGH, MEDIUM, LOW (for Trusted Advisor: ERROR, WARNING)
- Boolean flags: Use "true" or "false"
```

### Step 2: Write Detailed OpenAPI Descriptions

See `templates/security-action-group-schema.json` for complete example.

**Key elements:**
- Operation description with "Use this operation when..."
- Multiple user phrase examples
- Parameter descriptions with mapping guidance
- Default values clearly stated

### Step 3: Test Agent Understanding

```bash
# Test 1: Check if agent calls correct operation
User: "Check security status"
Expected: Calls checkSecurityStatus

# Test 2: Check parameter extraction
User: "Check security in Virginia"
Expected: Calls checkSecurityStatus with region="us-east-1"

# Test 3: Check service-specific request
User: "Show me high severity GuardDuty findings"
Expected: Calls getSecurityFindings with service="guardduty", severity="HIGH"

# Test 4: Check encryption request
User: "Are my S3 buckets encrypted?"
Expected: Calls checkStorageEncryption with services="s3"

# Test 5: Check network security
User: "Check if my load balancers are secure"
Expected: Calls checkNetworkSecurity with services="elb"
```

---

## Debugging Agent Tool Selection

### Step 1: Check Agent Trace

Enable agent tracing to see decision process:

```python
response = bedrock_agent_runtime.invoke_agent(
    agentId='AGENT_ID',
    agentAliasId='ALIAS_ID',
    sessionId='session-123',
    inputText='Check security status',
    enableTrace=True  # Enable tracing
)

# Check trace
for event in response['completion']:
    if 'trace' in event:
        trace = event['trace']['trace']
        print(json.dumps(trace, indent=2))
```

**Look for:**
- `orchestrationTrace` - Shows agent reasoning
- `invocationInput` - Shows which action group was selected
- `actionGroupInvocationInput` - Shows parameters extracted

### Step 2: Check CloudWatch Logs

Agent logs show reasoning:

```bash
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agent/AGENT_ID \
  --filter-pattern "orchestration"
```

**Look for:**
- "Selected action group: ..."
- "Extracted parameters: ..."
- "No matching action group found" ← Agent didn't understand

### Step 3: Test with Explicit Instructions

If agent not calling tools, test with explicit instruction:

```
User: "Use the checkSecurityStatus action to check security in us-east-1"
```

If this works but natural language doesn't, problem is in OpenAPI descriptions.

---

## Checklist: Agent Tool Selection

- [ ] Agent instructions describe all capabilities
- [ ] Agent instructions say to use action groups (not generic advice)
- [ ] Each operation has detailed description with "Use this when..."
- [ ] Each operation has 3-5 example user phrases
- [ ] Operation descriptions are distinct (no overlap)
- [ ] Parameter descriptions include mapping guidance
- [ ] Parameter descriptions include default values
- [ ] Tested with natural language queries
- [ ] Tested with region name variations
- [ ] Tested with service name variations
- [ ] Enabled agent tracing to verify selection
- [ ] Checked CloudWatch logs for reasoning

---

## Example: Before vs After

### Before (Agent Returns Generic Response)

**Agent Instructions:**
```
You are a helpful assistant.
```

**OpenAPI Description:**
```json
{
  "description": "Check security"
}
```

**Result:**
```
User: "Check security status"
Agent: "I can help you with security. What would you like to know?" ❌
```

### After (Agent Calls Tool)

**Agent Instructions:**
```
You are an AWS security chatbot. You have action groups to check security services, get findings, check encryption, and analyze network security. ALWAYS use action groups to get real-time AWS data.
```

**OpenAPI Description:**
```json
{
  "description": "Use this operation when the user asks about security service status, enabled services, or wants to check if security services like GuardDuty, Security Hub, Inspector are enabled. Examples: 'check security status', 'are security services enabled', 'what security services are running'."
}
```

**Result:**
```
User: "Check security status"
Agent: Calls checkSecurityStatus → Gets real data → Returns actual status ✅
```

---

## Related Files

- [Security Action Group Schema](../templates/security-action-group-schema.json) - Complete OpenAPI schema with proper descriptions
- [Complete Parameter Mapping](./COMPLETE-PARAMETER-MAPPING.md) - Parameter extraction guide
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md) - Master issues list
