#!/bin/bash
# Deploy AgentCore app (not Lambda) - zero interaction

set -e

REGION=${AWS_REGION:-us-east-1}
APP_FILE="/persistent/home/ubuntu/workspace/training/security-agent-app.py"
REQ_FILE="/persistent/home/ubuntu/workspace/training/requirements.txt"

echo "🚀 Deploying AgentCore app..."

# Configure
agentcore configure \
  -e "$APP_FILE" \
  --requirements-file "$REQ_FILE" \
  --region "$REGION" \
  --protocol MCP

# Launch to Runtime
agentcore launch

# Get endpoint
sleep 10
ENDPOINT=$(agentcore status --verbose | jq -r '.endpoint.url')

echo "✅ AgentCore app deployed: $ENDPOINT"
echo "$ENDPOINT" > /tmp/agentcore-endpoint.txt
