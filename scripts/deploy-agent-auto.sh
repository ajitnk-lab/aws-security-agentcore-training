#!/bin/bash
# Auto-deploy Bedrock Agent - zero interaction

set -e

REGION=${AWS_REGION:-us-east-1}
AGENT_NAME="SecurityAgent-$(date +%s)"

# Get Gateway URL
GATEWAY_URL=$(cat /tmp/gateway-url.txt 2>/dev/null || echo "")
[[ -z "$GATEWAY_URL" ]] && echo "❌ Run deploy-gateway-auto.sh first" && exit 1

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda list-functions --region "$REGION" --query "Functions[?contains(FunctionName, 'gateway') || contains(FunctionName, 'proxy')].FunctionArn | [0]" --output text)
[[ -z "$LAMBDA_ARN" ]] && echo "❌ No Lambda found" && exit 1

# Get or create role
ROLE_ARN=$(aws iam get-role --role-name BedrockAgentRole 2>/dev/null | jq -r '.Role.Arn' || \
  aws iam create-role --role-name BedrockAgentRole --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }' | jq -r '.Role.Arn')

# Attach policy
aws iam attach-role-policy --role-name BedrockAgentRole --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess 2>/dev/null || true

# Create agent
AGENT_ID=$(aws bedrock-agent create-agent \
  --agent-name "$AGENT_NAME" \
  --agent-resource-role-arn "$ROLE_ARN" \
  --foundation-model anthropic.claude-3-sonnet-20240229-v1:0 \
  --instruction "Use action groups to check AWS security." \
  --region "$REGION" \
  --query 'agent.agentId' --output text)

# Create action group
aws bedrock-agent create-agent-action-group \
  --agent-id "$AGENT_ID" \
  --agent-version DRAFT \
  --action-group-name SecurityActions \
  --action-group-executor "{\"lambda\": \"$LAMBDA_ARN\"}" \
  --function-schema "{\"functions\": [{\"name\": \"check_security\", \"description\": \"Check AWS security\", \"parameters\": {}}]}" \
  --region "$REGION"

# Add Lambda permission
aws lambda add-permission \
  --function-name "$LAMBDA_ARN" \
  --statement-id bedrock-agent-$AGENT_ID \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:$REGION:*:agent/$AGENT_ID" \
  --region "$REGION" 2>/dev/null || true

# Prepare agent
aws bedrock-agent prepare-agent --agent-id "$AGENT_ID" --region "$REGION"

echo "✅ Agent created: $AGENT_ID"
echo "$AGENT_ID" > /tmp/agent-id.txt
