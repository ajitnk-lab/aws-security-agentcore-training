#!/bin/bash
# Pre-test checklist - Run BEFORE testing agent
# Prevents: Testing too early, missing readiness issues

AGENT_ID="$1"
LAMBDA_NAME="$2"

if [ -z "$AGENT_ID" ] || [ -z "$LAMBDA_NAME" ]; then
    echo "Usage: ./pre-test-checklist.sh <agent-id> <lambda-name>"
    exit 1
fi

echo "=========================================="
echo "PRE-TEST CHECKLIST"
echo "=========================================="
echo ""

PASSED=0
FAILED=0

# Check 1: Agent exists and is PREPARED
echo "1️⃣  Checking agent status..."
STATUS=$(aws bedrock-agent get-agent --agent-id "$AGENT_ID" --query 'agent.agentStatus' --output text 2>/dev/null)
if [ "$STATUS" = "PREPARED" ]; then
    echo "   ✅ Agent is PREPARED"
    ((PASSED++))
else
    echo "   ❌ Agent status: $STATUS (expected PREPARED)"
    ((FAILED++))
fi
echo ""

# Check 2: Lambda exists
echo "2️⃣  Checking Lambda function..."
if aws lambda get-function --function-name "$LAMBDA_NAME" &>/dev/null; then
    echo "   ✅ Lambda function exists"
    ((PASSED++))
else
    echo "   ❌ Lambda function not found: $LAMBDA_NAME"
    ((FAILED++))
fi
echo ""

# Check 3: Lambda has Bedrock permission
echo "3️⃣  Checking Lambda permissions..."
POLICY=$(aws lambda get-policy --function-name "$LAMBDA_NAME" --query 'Policy' --output text 2>/dev/null)
if echo "$POLICY" | grep -q "bedrock.amazonaws.com"; then
    echo "   ✅ Lambda has Bedrock permission"
    ((PASSED++))
else
    echo "   ❌ Lambda missing Bedrock permission"
    echo "      Fix: aws lambda add-permission --function-name $LAMBDA_NAME ..."
    ((FAILED++))
fi
echo ""

# Check 4: Action groups exist and enabled
echo "4️⃣  Checking action groups..."
AG_COUNT=$(aws bedrock-agent list-agent-action-groups \
    --agent-id "$AGENT_ID" \
    --agent-version DRAFT \
    --query 'length(actionGroupSummaries)' \
    --output text 2>/dev/null)

if [ "$AG_COUNT" -gt 0 ]; then
    echo "   ✅ Found $AG_COUNT action group(s)"
    ((PASSED++))
else
    echo "   ❌ No action groups found"
    ((FAILED++))
fi
echo ""

# Check 5: Wait for stabilization
echo "5️⃣  Checking last update time..."
UPDATED=$(aws bedrock-agent get-agent --agent-id "$AGENT_ID" --query 'agent.updatedAt' --output text 2>/dev/null)
UPDATED_EPOCH=$(date -d "$UPDATED" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$UPDATED" +%s 2>/dev/null)
NOW_EPOCH=$(date +%s)
AGE=$((NOW_EPOCH - UPDATED_EPOCH))

if [ "$AGE" -gt 30 ]; then
    echo "   ✅ Agent stable (last updated ${AGE}s ago)"
    ((PASSED++))
else
    echo "   ⚠️  Agent recently updated (${AGE}s ago)"
    echo "      Recommend waiting 30s for stabilization"
    ((FAILED++))
fi
echo ""

# Summary
echo "=========================================="
echo "CHECKLIST SUMMARY"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED"
    echo ""
    echo "Agent is ready for testing."
    echo "Recommended: Wait 10-15 seconds before first invocation."
    exit 0
else
    echo "❌ SOME CHECKS FAILED"
    echo ""
    echo "Fix the issues above before testing."
    exit 1
fi
