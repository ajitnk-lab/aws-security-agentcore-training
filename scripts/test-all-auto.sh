#!/bin/bash
# Auto-test entire stack - zero interaction

set -e

REGION=${AWS_REGION:-us-east-1}
AGENT_ID=$(cat /tmp/agent-id.txt 2>/dev/null || echo "")

[[ -z "$AGENT_ID" ]] && echo "❌ Run deploy-agent-auto.sh first" && exit 1

echo "⏳ Waiting for agent ready..."
sleep 45

# Create alias
ALIAS_ID=$(aws bedrock-agent create-agent-alias \
  --agent-id "$AGENT_ID" \
  --agent-alias-name live \
  --region "$REGION" \
  --query 'agentAlias.agentAliasId' --output text 2>/dev/null || echo "TSTALIASID")

sleep 15

# Test
aws bedrock-agent-runtime invoke-agent \
  --agent-id "$AGENT_ID" \
  --agent-alias-id "$ALIAS_ID" \
  --session-id "test-$(date +%s)" \
  --input-text "Check security in us-east-1" \
  --region "$REGION" \
  /tmp/agent-response.txt

cat /tmp/agent-response.txt
echo "✅ Test complete"
