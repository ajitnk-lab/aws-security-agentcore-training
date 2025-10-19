#!/bin/bash
# Auto-deploy Gateway - no questions asked
# Detects MCP server, deploys to Runtime, creates Gateway

set -e

REGION=${AWS_REGION:-us-east-1}
MCP_DIR="/persistent/home/ubuntu/workspace/training/well-arch-sec-mcp-server-tets"

echo "🚀 Auto-deploying Gateway..."

# 1. Find MCP server entrypoint
ENTRYPOINT=$(find "$MCP_DIR" -name "server.py" -o -name "main.py" -o -name "app.py" | head -1)
[[ -z "$ENTRYPOINT" ]] && echo "❌ No MCP server found" && exit 1

# 2. Deploy to Runtime
echo "📦 Deploying to AgentCore Runtime..."
agentcore configure -e "$ENTRYPOINT" --region "$REGION" 2>/dev/null || true
agentcore launch --agent $(basename "$ENTRYPOINT" .py)

# 3. Get Runtime endpoint
ENDPOINT=$(agentcore status --verbose | jq -r '.endpoint.url' 2>/dev/null)
[[ -z "$ENDPOINT" ]] && echo "❌ No endpoint found" && exit 1

# 4. Create Gateway
echo "🌐 Creating Gateway..."
GATEWAY_NAME="SecurityGateway-$(date +%s)"
agentcore gateway create-mcp-gateway --name "$GATEWAY_NAME" --region "$REGION"

# 5. Get Gateway details
GATEWAY_ARN=$(aws bedrock-agent list-gateways --region "$REGION" --query "gateways[?name=='$GATEWAY_NAME'].arn | [0]" --output text)
GATEWAY_URL=$(aws bedrock-agent get-gateway --gateway-id "${GATEWAY_ARN##*/}" --region "$REGION" --query 'gateway.url' --output text)

# 6. Create target
echo "🎯 Attaching target..."
agentcore gateway create-mcp-gateway-target \
  --gateway-arn "$GATEWAY_ARN" \
  --gateway-url "$GATEWAY_URL" \
  --target-type lambda \
  --region "$REGION"

echo "✅ Gateway deployed: $GATEWAY_URL"
echo "$GATEWAY_URL" > /tmp/gateway-url.txt
