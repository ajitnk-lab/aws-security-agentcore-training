# Agent Troubleshooting Workflow

## The Problem You Faced

1. **Agent not ready** - Testing before agent reached stable PREPARED state
2. **Log lag** - Checking logs too early, before events appeared
3. **Lost in troubleshooting** - No systematic approach to find root cause

## The Solution: Systematic Workflow

### Step 1: Pre-Test Checklist (ALWAYS RUN FIRST)

```bash
./scripts/pre-test-checklist.sh AGENT_ID SecurityLambda
```

**Checks:**
- ✅ Agent is PREPARED
- ✅ Lambda exists
- ✅ Lambda has Bedrock permission
- ✅ Action groups exist and enabled
- ✅ Agent stable (not recently updated)

**If any check fails:** Fix it before testing. Don't proceed.

### Step 2: Wait for Agent Ready (After Changes)

```bash
# After creating/updating agent or action groups
python3 scripts/wait-for-agent-ready.py AGENT_ID SecurityLambda
```

**What it does:**
- Polls agent status every 5 seconds
- Waits for 3 consecutive PREPARED checks (stability)
- Checks action groups are enabled
- Verifies Lambda permissions
- Shows recent logs

**Wait time:** 30-60 seconds typical, up to 5 minutes max

### Step 3: Stabilization Wait (CRITICAL)

After agent shows PREPARED, **wait 10-15 seconds** before first invocation.

**Why?** AWS internal routing and caching needs time to propagate.

```bash
echo "Agent ready. Waiting 15s for stabilization..."
sleep 15
echo "Ready to test!"
```

### Step 4: Test Invocation

```bash
# Test with Web API Lambda or direct invoke
aws bedrock-agent-runtime invoke-agent \
  --agent-id AGENT_ID \
  --agent-alias-id ALIAS_ID \
  --session-id test-$(date +%s) \
  --input-text "Check security status for EC2" \
  response.txt
```

### Step 5: Monitor Logs (If Issues)

```bash
# Check logs from last 5 minutes
./scripts/monitor-agent-logs.sh SecurityLambda 5

# Or follow in real-time
aws logs tail /aws/lambda/SecurityLambda --follow
```

**Look for:**
- `DependencyFailedException` → Lambda permission issue
- `Task timed out` → Lambda timeout issue
- `ERROR` or `Exception` → Lambda code error
- No logs at all → Lambda never invoked (permission issue)

### Step 6: Systematic Debugging

If test fails, check in this order:

#### 6.1 Agent Status
```bash
aws bedrock-agent get-agent --agent-id AGENT_ID | jq '.agent.agentStatus'
```
Expected: `"PREPARED"`

#### 6.2 Action Group State
```bash
aws bedrock-agent list-agent-action-groups \
  --agent-id AGENT_ID \
  --agent-version DRAFT | jq '.actionGroupSummaries[].actionGroupState'
```
Expected: `"ENABLED"`

#### 6.3 Lambda Permission
```bash
aws lambda get-policy --function-name SecurityLambda | jq '.Policy | fromjson'
```
Expected: Statement with `bedrock.amazonaws.com` principal

#### 6.4 Lambda Logs
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/SecurityLambda \
  --start-time $(($(date +%s) - 300))000 \
  --query 'events[*].message' \
  --output text
```

#### 6.5 Test Lambda Directly
```bash
# Create test event
cat > test-event.json << 'EOF'
{
  "messageVersion": "1.0",
  "agent": {"name": "test", "id": "test", "alias": "test", "version": "DRAFT"},
  "actionGroup": "SecurityActions",
  "apiPath": "/check-security-status",
  "httpMethod": "POST",
  "parameters": [{"name": "resourceType", "type": "string", "value": "ec2"}],
  "sessionId": "test",
  "inputText": "test"
}
EOF

# Invoke
aws lambda invoke \
  --function-name SecurityLambda \
  --payload file://test-event.json \
  response.json

# Validate response
python3 scripts/validate-action-group-response.py response.json
```

## Common Failure Patterns

### Pattern 1: "Agent not ready" Error
**Symptom:** Invocation fails immediately
**Cause:** Agent status is not PREPARED
**Fix:** Run `wait-for-agent-ready.py` and wait for stable state

### Pattern 2: DependencyFailedException
**Symptom:** Agent invokes but Lambda never executes
**Cause:** Missing Lambda resource-based policy
**Fix:** Add Lambda permission for bedrock.amazonaws.com

### Pattern 3: No Logs Appear
**Symptom:** Test fails, but no Lambda logs
**Cause:** Lambda never invoked (permission issue) OR checking logs too early
**Fix:** 
1. Wait 30 seconds after test
2. Check Lambda permission
3. Check action group has correct Lambda ARN

### Pattern 4: Lambda Timeout
**Symptom:** Logs show "Task timed out after 3.00 seconds"
**Cause:** Lambda timeout too short
**Fix:** Increase Lambda timeout to 30+ seconds

### Pattern 5: Wrong Response Format
**Symptom:** Lambda executes but agent fails to parse response
**Cause:** Response doesn't match required format
**Fix:** Validate response with `validate-action-group-response.py`

## Best Practice Workflow

### After Creating Agent
```bash
# 1. Create agent and action groups
aws bedrock-agent create-agent ...
aws bedrock-agent create-agent-action-group ...

# 2. Prepare agent
aws bedrock-agent prepare-agent --agent-id AGENT_ID

# 3. Wait for ready
python3 scripts/wait-for-agent-ready.py AGENT_ID SecurityLambda

# 4. Stabilization wait
sleep 15

# 5. Test
# ... your test code ...
```

### After Updating Agent
```bash
# 1. Make changes
aws bedrock-agent update-agent-action-group ...

# 2. Prepare agent
aws bedrock-agent prepare-agent --agent-id AGENT_ID

# 3. Wait for ready
python3 scripts/wait-for-agent-ready.py AGENT_ID SecurityLambda

# 4. Stabilization wait
sleep 15

# 5. Test
# ... your test code ...
```

### Before Every Test
```bash
# Run pre-test checklist
./scripts/pre-test-checklist.sh AGENT_ID SecurityLambda

# If passes, proceed with test
# If fails, fix issues first
```

## Time Expectations

| Operation | Expected Time | Notes |
|-----------|--------------|-------|
| Agent prepare | 10-30s | After create/update |
| Stabilization | 10-15s | After PREPARED state |
| Log appearance | 5-30s | After invocation |
| Total wait (create → test) | 30-60s | Typical case |
| Total wait (update → test) | 20-45s | Typical case |

## Tools Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `pre-test-checklist.sh` | Verify readiness | Before every test |
| `wait-for-agent-ready.py` | Wait for stable state | After create/update |
| `monitor-agent-logs.sh` | Check recent logs | When troubleshooting |
| `validate-action-group-response.py` | Validate Lambda response | Before deployment |
| `bedrock-agent-inventory.py` | List all agents | When confused about IDs |
| `which-agent.sh` | Show active config | Before making changes |

## Related Documentation

- [DependencyFailedException Guide](./BEDROCK-AGENT-DEPENDENCY-FAILED-EXCEPTION.md)
- [Agent Inventory Tool](../scripts/bedrock-agent-inventory.py)
- [Response Validator](../scripts/validate-action-group-response.py)
