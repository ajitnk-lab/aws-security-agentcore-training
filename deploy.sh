#!/bin/bash
set -e

echo "🚀 Deploying AWS Security AgentCore Solution"
echo "=============================================="

REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Deploy CDK Infrastructure
echo "📦 Step 1/5: Deploying CDK infrastructure..."
cd infrastructure
cdk deploy --require-approval never
cd ..
echo "✅ CDK deployed"
echo ""

# Step 2: Setup OAuth/Cognito
echo "🔐 Step 2/5: Setting up OAuth/Cognito..."
python3 << 'EOF'
import json
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

client = GatewayClient(region_name="us-east-1")
cognito = client.create_oauth_authorizer_with_cognito("SecurityGateway")

with open('auth-config.json', 'w') as f:
    json.dump(cognito['authorizer_config'], f)
with open('client-info.json', 'w') as f:
    json.dump(cognito['client_info'], f)
    
print(f"Client ID: {cognito['client_info']['client_id']}")
EOF
echo "✅ OAuth configured"
echo ""

# Step 3: Deploy MCP Server to Runtime
echo "🏃 Step 3/5: Deploying MCP server to AgentCore Runtime..."
agentcore configure -e security-agent-app.py --region $REGION --non-interactive
agentcore launch
RUNTIME_ENDPOINT=$(agentcore status --verbose | jq -r '.endpoint.url')
echo "Runtime endpoint: $RUNTIME_ENDPOINT"
echo "✅ Runtime deployed"
echo ""

# Step 4: Create Gateway
echo "🌐 Step 4/5: Creating AgentCore Gateway..."
python3 << 'EOF'
import json
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

client = GatewayClient(region_name="us-east-1")

with open('auth-config.json') as f:
    auth_config = json.load(f)

gateway = client.create_mcp_gateway(
    name="SecurityGateway",
    role_arn=None,
    authorizer_config=auth_config,
    enable_semantic_search=True
)

client.fix_iam_permissions(gateway)

# Create Lambda target
lambda_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="SecurityMCPTools",
    target_type="lambda",
    target_payload=None
)

with open('gateway-config.json', 'w') as f:
    json.dump({
        'gateway_url': gateway['gatewayUrl'],
        'gateway_id': gateway['gatewayId']
    }, f)

print(f"Gateway URL: {gateway['gatewayUrl']}")
EOF
echo "✅ Gateway created"
echo ""

# Step 5: Create Bedrock Agent
echo "🤖 Step 5/5: Creating Bedrock Agent..."
python3 scripts/create-bedrock-agent.py
echo "✅ Agent created"
echo ""

echo "=============================================="
echo "✅ Deployment Complete!"
echo ""
echo "Next steps:"
echo "1. Test: ./scripts/test-all-auto.sh"
echo "2. View logs: ./scripts/monitor-agent-logs.sh"
echo "3. Check status: agentcore status"
