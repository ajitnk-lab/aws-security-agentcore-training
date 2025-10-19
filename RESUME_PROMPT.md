# Resume Prompt for Q

I'm building a complete AWS Security AgentCore solution from MCP server to UI. We've completed the planning phase and created detailed documentation.

## What We've Done

1. **Documented 35+ issues and solutions** in `/persistent/home/ubuntu/workspace/training/wikis/`
   - All issues from Bedrock Agent, Gateway, Lambda, OAuth, parameter mapping
   - Root causes, solutions, prevention strategies

2. **Created GitHub repo:** https://github.com/ajitnk-lab/aws-security-agentcore-training
   - All documentation pushed
   - Deployment scripts created

3. **Clarified Architecture (5 Questions Answered):**
   - Q1: AgentCore Runtime only (no Lambda for MCP server)
   - Q2: OAuth/Cognito setup using Python SDK helper once, save configs
   - Q3: Gateway target = Lambda (auto-created), not direct Runtime endpoint
   - Q4: Tool names use PascalCase, Gateway adds `${target_name}__${tool_name}` prefix
   - Q5: Bedrock Agent → Security Lambda → Gateway → Lambda Target → Runtime

4. **Created TODO List (ID: 1760860236765)** with 50 tasks:
   - Layer 0: Project setup (6 tasks)
   - Layer 1: MCP Server (3 tasks)
   - Layer 2: AgentCore Runtime (4 tasks)
   - Layer 3: AgentCore Gateway (7 tasks)
   - Layer 4: Security Lambda (8 tasks)
   - Layer 5: Bedrock Agent (10 tasks)
   - Layer 6: Web API (6 tasks)
   - Layer 7: Frontend UI (6 tasks)

## What to Do Next

**Load the TODO list and start executing:**

```
Load TODO: 1760860236765
Start with Layer 0.1: Create new project folder structure
```

## Key Files to Reference

- **Documentation:** `/persistent/home/ubuntu/workspace/training/wikis/ALL-ISSUES-AND-SOLUTIONS.md`
- **Working MCP Server:** `/persistent/home/ubuntu/workspace/aws-security-agentcore-chatbot/well_architected_security_mcp_server/server.py`
- **Working Lambda:** `/persistent/home/ubuntu/workspace/aws-security-agentcore-chatbot/gateway_proxy_lambda_working.py`
- **Parameter Mapping:** `/persistent/home/ubuntu/workspace/training/templates/complete-parameter-mapper.py`

## Architecture Flow

```
User → Frontend (S3/CloudFront)
  → Web API Lambda (API Gateway)
    → Bedrock Agent
      → Security Lambda (gateway_proxy_lambda.py)
        → AgentCore Gateway (OAuth)
          → Lambda Target (auto-created)
            → AgentCore Runtime
              → MCP Server (6 tools)
```

## 6 MCP Tools (PascalCase)

1. CheckSecurityServices
2. GetSecurityFindings
3. CheckStorageEncryption
4. CheckNetworkSecurity
5. ListServicesInRegion
6. GetStoredSecurityContext

Gateway adds prefix: `SecurityMCPTools__CheckSecurityServices` etc.

## Critical Points

- Use Function Details (not OpenAPI) for Bedrock Agent action groups
- Security Lambda handles OAuth token + parameter mapping
- Wait 30-60s after agent prepare for stabilization
- Tool descriptions must include "Use this when..." with examples

## Command to Resume

```
Load TODO list 1760860236765 and start executing Layer 0.1
```
