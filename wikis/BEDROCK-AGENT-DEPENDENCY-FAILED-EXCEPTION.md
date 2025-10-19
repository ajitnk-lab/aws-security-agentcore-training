# DependencyFailedException - Root Cause & Solutions

## What Is DependencyFailedException?

`DependencyFailedException` occurs when Bedrock Agent **cannot invoke the target Lambda function** for an action group. The error indicates a dependency (Lambda, Bedrock, or STS) failed during agent invocation.

## Root Causes (In Order of Frequency)

### 1. Missing Lambda Resource-Based Policy ⭐ MOST COMMON

**Problem:** Lambda function doesn't have permission for Bedrock to invoke it.

**Symptom:** Agent invokes action group → Lambda never executes → DependencyFailedException

**Solution:**
```bash
# Add resource-based policy to Lambda
aws lambda add-permission \
  --function-name SecurityLambda \
  --statement-id bedrock-agent-invoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:123456789012:agent/AGENT_ID" \
  --source-account 123456789012
```

**CDK Solution:**
```typescript
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';

const securityLambda = new lambda.Function(this, 'SecurityLambda', {
  // ... function config
});

// Add resource-based policy
securityLambda.addPermission('BedrockAgentInvoke', {
  principal: new iam.ServicePrincipal('bedrock.amazonaws.com'),
  action: 'lambda:InvokeFunction',
  sourceArn: `arn:aws:bedrock:${this.region}:${this.account}:agent/${agentId}`,
  sourceAccount: this.account,
});
```

### 2. Wrong Lambda Response Format

**Problem:** Lambda returns response but format doesn't match Bedrock requirements.

**Symptom:** Lambda executes successfully → Agent fails to parse response → DependencyFailedException

**Common Mistakes:**
- `body` is dict instead of JSON string
- Missing `messageVersion`
- Missing required fields (`actionGroup`, `apiPath`, `httpMethod`, `httpStatusCode`)
- Wrong `messageVersion` (must be `"1.0"`)

**Solution:** Use validator before deployment
```bash
python3 scripts/validate-action-group-response.py test-response.json
```

**Correct Format:**
```python
import json

def lambda_handler(event, context):
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event['actionGroup'],
            'apiPath': event['apiPath'],
            'httpMethod': event['httpMethod'],
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'status': 'success'})  # MUST be string
                }
            }
        }
    }
```

### 3. Agent Not in PREPARED State

**Problem:** Agent exists but hasn't been prepared after configuration changes.

**Symptom:** Agent invocation fails immediately → DependencyFailedException

**Solution:**
```bash
# Prepare agent after any changes
aws bedrock-agent prepare-agent --agent-id AGENT_ID

# Wait for PREPARED state
aws bedrock-agent get-agent --agent-id AGENT_ID | jq '.agent.agentStatus'
```

### 4. Lambda Timeout or Error

**Problem:** Lambda times out or throws unhandled exception.

**Symptom:** Lambda starts but doesn't complete → DependencyFailedException

**Solution:**
- Increase Lambda timeout (default 3s → 30s+)
- Add try/catch to return proper error response
- Check CloudWatch logs for Lambda errors

```python
def lambda_handler(event, context):
    try:
        result = perform_action(event)
        return format_success_response(event, result)
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event['actionGroup'],
                'apiPath': event['apiPath'],
                'httpMethod': event['httpMethod'],
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({'error': str(e)})
                    }
                }
            }
        }
```

### 5. Agent Service Role Missing Permissions

**Problem:** Agent's IAM role can't invoke Lambda or access resources.

**Symptom:** Agent can't reach Lambda → DependencyFailedException

**Solution:** Verify agent service role has:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

Note: Agent service role does NOT need Lambda invoke permissions - that's handled by Lambda's resource-based policy.

### 6. Wrong Agent ID or Alias

**Problem:** Web API Lambda invokes wrong agent ID or non-existent alias.

**Symptom:** Agent not found → DependencyFailedException

**Solution:**
```python
# Verify agent exists and is PREPARED
import boto3
bedrock_agent = boto3.client('bedrock-agent')

response = bedrock_agent.get_agent(agentId='AGENT_ID')
print(f"Status: {response['agent']['agentStatus']}")

# List aliases
aliases = bedrock_agent.list_agent_aliases(agentId='AGENT_ID')
print(f"Aliases: {aliases['agentAliasSummaries']}")
```

## Debugging Workflow

### Step 1: Check Lambda Resource-Based Policy
```bash
aws lambda get-policy --function-name SecurityLambda | jq '.Policy | fromjson'
```

**Expected:** Statement with `bedrock.amazonaws.com` principal and `lambda:InvokeFunction` action.

### Step 2: Test Lambda Directly
```bash
# Create test event matching Bedrock format
cat > test-event.json << 'EOF'
{
  "messageVersion": "1.0",
  "agent": {"name": "test", "id": "test", "alias": "test", "version": "DRAFT"},
  "actionGroup": "SecurityActions",
  "apiPath": "/check-security-status",
  "httpMethod": "POST",
  "parameters": [{"name": "resourceType", "type": "string", "value": "ec2"}],
  "sessionId": "test-session",
  "inputText": "test"
}
EOF

# Invoke Lambda
aws lambda invoke \
  --function-name SecurityLambda \
  --payload file://test-event.json \
  response.json

# Check response format
python3 scripts/validate-action-group-response.py response.json
```

### Step 3: Check Agent State
```bash
aws bedrock-agent get-agent --agent-id AGENT_ID | jq '.agent.agentStatus'
```

**Expected:** `"PREPARED"` or `"VERSIONED"`

### Step 4: Check CloudWatch Logs

**Lambda Logs:**
```bash
aws logs tail /aws/lambda/SecurityLambda --follow
```

**Agent Logs:** (if enabled)
```bash
aws logs tail /aws/bedrock/agent/AGENT_ID --follow
```

### Step 5: Verify Action Group Configuration
```bash
aws bedrock-agent get-agent-action-group \
  --agent-id AGENT_ID \
  --agent-version DRAFT \
  --action-group-id ACTION_GROUP_ID
```

**Check:**
- `actionGroupExecutor.lambda` points to correct Lambda ARN
- `apiSchema` is valid OpenAPI 3.0.0
- `actionGroupState` is `ENABLED`

## Prevention Checklist

Before deploying agent + action group:

- [ ] Lambda has resource-based policy for `bedrock.amazonaws.com`
- [ ] Lambda response format validated with script
- [ ] Agent is in PREPARED state
- [ ] Lambda timeout ≥ 30 seconds
- [ ] Lambda has error handling with proper response format
- [ ] OpenAPI schema validated (version 3.0.0, has operationId)
- [ ] Agent service role has `bedrock:InvokeModel` permission
- [ ] Action group points to correct Lambda ARN
- [ ] Tested Lambda directly with sample event

## Quick Fix Script

```bash
#!/bin/bash
# fix-dependency-failed.sh

AGENT_ID="$1"
LAMBDA_NAME="$2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-east-1"

echo "Adding Lambda permission for Bedrock Agent..."
aws lambda add-permission \
  --function-name "$LAMBDA_NAME" \
  --statement-id bedrock-agent-invoke-$(date +%s) \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:$REGION:$ACCOUNT_ID:agent/$AGENT_ID" \
  --source-account "$ACCOUNT_ID"

echo "Preparing agent..."
aws bedrock-agent prepare-agent --agent-id "$AGENT_ID"

echo "Waiting for PREPARED state..."
while true; do
  STATUS=$(aws bedrock-agent get-agent --agent-id "$AGENT_ID" | jq -r '.agent.agentStatus')
  echo "Current status: $STATUS"
  if [ "$STATUS" = "PREPARED" ]; then
    echo "✅ Agent is ready"
    break
  fi
  sleep 5
done
```

**Usage:**
```bash
chmod +x fix-dependency-failed.sh
./fix-dependency-failed.sh AGENT_ID SecurityLambda
```

## Tracking Multiple Agents/Versions/Action Groups

**Problem:** With multiple agents, versions, aliases, and action groups, you lose track of which one to use.

**Solution:** Use inventory and state tracking tools.

### Get Complete Inventory
```bash
# Scan all agents and their components
python3 scripts/bedrock-agent-inventory.py

# Output: agent-inventory.json with full details
```

### Track Active Configuration
```bash
# Quick reference - which agent/alias to use right now
./scripts/which-agent.sh
```

**Output:**
```
🤖 Agent: SecurityChatbotAgent
   ID: AGENT123
   Alias: prod (TSTALIASID)
   Status: PREPARED

⚡ Action Groups:
   • SecurityActions (ENABLED)
     Lambda: arn:aws:lambda:us-east-1:123456789012:function:SecurityLambda
     Operations: checkSecurityStatus, listFindings

🔧 Environment Variables for Lambda:
   export AGENT_ID=AGENT123
   export AGENT_ALIAS_ID=TSTALIASID
```

### Update State After Changes
```bash
# After creating/updating agent, update state file
vim templates/agent-state.json

# Add deployment history entry
{
  "date": "2025-10-19T06:00:00Z",
  "action": "Added new action group",
  "agent_id": "AGENT123",
  "notes": "Added ComplianceActions action group"
}
```

### Best Practice Workflow
1. **Before making changes:** Run `which-agent.sh` to see current state
2. **Make changes:** Create/update agent/action group
3. **Update inventory:** Run `bedrock-agent-inventory.py`
4. **Update state:** Edit `agent-state.json` with new IDs
5. **Verify:** Run `which-agent.sh` to confirm

## Related Documentation

- [Lambda Response Format Template](../templates/action-group-lambda-response.py)
- [OpenAPI Schema Template](../templates/bedrock-action-group-schema-template.json)
- [Response Validator](../scripts/validate-action-group-response.py)
- [Schema Validator](../scripts/validate-openapi-schema.py)
- [Agent Inventory Tool](../scripts/bedrock-agent-inventory.py)
- [Agent State Tracker](../scripts/which-agent.sh)
