#!/bin/bash
set -e

echo "🧹 Cleaning up AWS Security AgentCore Solution"
echo "=============================================="

# Delete Bedrock Agent
echo "Deleting Bedrock Agent..."
AGENT_ID=$(cat agent-state.json 2>/dev/null | jq -r '.agent_id' || echo "")
if [ ! -z "$AGENT_ID" ]; then
    aws bedrock-agent delete-agent --agent-id $AGENT_ID --region us-east-1 || true
fi

# Delete Gateway
echo "Deleting Gateway..."
GATEWAY_ID=$(cat gateway-config.json 2>/dev/null | jq -r '.gateway_id' || echo "")
if [ ! -z "$GATEWAY_ID" ]; then
    python3 << EOF
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json

with open('gateway-config.json') as f:
    config = json.load(f)
with open('client-info.json') as f:
    client_info = json.load(f)

client = GatewayClient(region_name="us-east-1")
client.cleanup_gateway(config['gateway_id'], client_info)
EOF
fi

# Delete Runtime
echo "Deleting AgentCore Runtime..."
agentcore delete || true

# Delete CDK Stack
echo "Deleting CDK infrastructure..."
cd infrastructure
cdk destroy --force
cd ..

# Clean up config files
rm -f auth-config.json client-info.json gateway-config.json agent-state.json

echo "✅ Cleanup complete!"
