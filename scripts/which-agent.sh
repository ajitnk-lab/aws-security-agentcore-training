#!/bin/bash
# Quick script to show which agent/alias/action group to use

STATE_FILE="templates/agent-state.json"

if [ ! -f "$STATE_FILE" ]; then
    echo "❌ State file not found: $STATE_FILE"
    echo "Run: python3 scripts/bedrock-agent-inventory.py"
    exit 1
fi

echo "📋 CURRENT ACTIVE CONFIGURATION"
echo "================================"
echo ""

AGENT_ID=$(jq -r '.active_agent.agent_id' "$STATE_FILE")
AGENT_NAME=$(jq -r '.active_agent.agent_name' "$STATE_FILE")
ALIAS_ID=$(jq -r '.active_agent.alias_id' "$STATE_FILE")
ALIAS_NAME=$(jq -r '.active_agent.alias_name' "$STATE_FILE")
STATUS=$(jq -r '.active_agent.status' "$STATE_FILE")

echo "🤖 Agent: $AGENT_NAME"
echo "   ID: $AGENT_ID"
echo "   Alias: $ALIAS_NAME ($ALIAS_ID)"
echo "   Status: $STATUS"
echo ""

echo "⚡ Action Groups:"
jq -r '.action_groups[] | "   • \(.name) (\(.state))\n     Lambda: \(.lambda_arn)\n     Operations: \(.operations | join(", "))"' "$STATE_FILE"
echo ""

echo "🔧 Environment Variables for Lambda:"
echo "   export AGENT_ID=$AGENT_ID"
echo "   export AGENT_ALIAS_ID=$ALIAS_ID"
echo ""

echo "📝 Web API Lambda Invocation:"
echo "   bedrock_agent_runtime.invoke_agent("
echo "       agentId='$AGENT_ID',"
echo "       agentAliasId='$ALIAS_ID',"
echo "       sessionId='...',"
echo "       inputText='...'"
echo "   )"
echo ""

echo "📅 Last Updated: $(jq -r '.active_agent.last_updated' "$STATE_FILE")"
