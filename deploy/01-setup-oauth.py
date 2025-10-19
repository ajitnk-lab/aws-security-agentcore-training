#!/usr/bin/env python3
"""Step 1: Setup OAuth/Cognito for Gateway"""
import json
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

REGION = "us-east-1"
GATEWAY_NAME = "SecurityGateway"

print("🔐 Creating OAuth/Cognito...")
client = GatewayClient(region_name=REGION)
cognito = client.create_oauth_authorizer_with_cognito(GATEWAY_NAME)

# Save configs
with open('/tmp/auth-config.json', 'w') as f:
    json.dump(cognito['authorizer_config'], f)
    
with open('/tmp/client-info.json', 'w') as f:
    json.dump(cognito['client_info'], f)

print(f"✅ OAuth created")
print(f"Client ID: {cognito['client_info']['client_id']}")
