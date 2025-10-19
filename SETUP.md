# Setup Guide - Deploy in New AWS Account

## Prerequisites

1. **AWS Account** with admin access
2. **AWS CLI** configured: `aws configure`
3. **Python 3.10+** installed
4. **Node.js 18+** (for CDK)
5. **Docker** installed and running

## One-Time Setup (5 minutes)

```bash
# Clone repo
git clone https://github.com/ajitnk-lab/aws-security-agentcore-training.git
cd aws-security-agentcore-training

# Install dependencies
pip install -r requirements.txt
npm install -g aws-cdk
pip install bedrock-agentcore-starter-toolkit

# Bootstrap CDK (first time only in account/region)
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

## Deploy Complete Solution (One Command)

```bash
./deploy.sh
```

That's it! The script will:
1. Deploy CDK infrastructure (IAM roles, Lambda)
2. Setup OAuth/Cognito for Gateway
3. Deploy MCP server to AgentCore Runtime
4. Create Gateway with Lambda target
5. Create Bedrock Agent with action group
6. Test end-to-end

**Time:** ~10 minutes

## What Gets Deployed

```
├── AgentCore Runtime (MCP server with 6 tools)
├── AgentCore Gateway (with OAuth)
├── Security Lambda (Gateway proxy)
├── Bedrock Agent (with action group)
└── IAM Roles & Policies
```

## Verify Deployment

```bash
# Check all components
./scripts/verify-deployment.sh
```

## Clean Up

```bash
./cleanup.sh
```

## Manual Step-by-Step (if needed)

See [DEPLOYMENT_FLOW.md](./DEPLOYMENT_FLOW.md) for detailed steps.
