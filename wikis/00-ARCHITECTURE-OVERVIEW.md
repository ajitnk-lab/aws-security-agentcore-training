# Multi-Layer Bedrock Agent Architecture - Complete Guide

## Architecture Overview

Based on your deployment flow, this is a **9-layer architecture** for a security chatbot powered by Amazon Bedrock Agents:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Frontend (React UI on S3)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP POST
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 2: API Gateway (REST API)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ Lambda Proxy Integration
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 3: Web API Lambda (chatbot-web-api)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ InvokeAgent API
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 4: Bedrock Agent (security-chatbot-agent)            │
│           - Claude 3 Haiku Model                             │
│           - Agent Orchestration                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ Action Group Invocation
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 5: Agent Action Group (security-lambda)               │
│           - 5 Security Tools                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │ Lambda Invocation
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 6: Security Lambda (bedrock-gateway-proxy)           │
└──────────────────────┬──────────────────────────────────────┘
                       │ AWS SDK Calls
┌──────────────────────▼──────────────────────────────────────┐
│  Layer 7: AWS Security Services                             │
│           - GuardDuty, Security Hub, S3, EC2                 │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Layer 8: AgentCore Gateway (MCP Server)                    │
│           - OAuth Authentication                             │
│           - 6 MCP Tools                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Layer 9: AgentCore Runtime                                 │
│           - Container-based Agent Hosting                    │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### **Layer 1: Frontend (S3 Static Website)**
- **Purpose**: User interface for chatbot interaction
- **Technology**: React application
- **Hosting**: S3 static website hosting
- **Endpoint**: HTTP (not HTTPS)

### **Layer 2: API Gateway**
- **Purpose**: HTTP endpoint for frontend requests
- **Type**: REST API
- **Integration**: Lambda proxy integration
- **Method**: POST to `/chat`

### **Layer 3: Web API Lambda**
- **Purpose**: Bridge between API Gateway and Bedrock Agent
- **Runtime**: Python 3.9
- **Role**: GatewayProxyLambdaRole
- **Function**: Invoke Bedrock Agent and return response

### **Layer 4: Bedrock Agent**
- **Purpose**: AI orchestration and decision-making
- **Model**: Claude 3 Haiku (fast, cost-effective)
- **Status**: PREPARED (ready for invocation)
- **Capabilities**: Natural language understanding, tool selection

### **Layer 5: Agent Action Group**
- **Purpose**: Define available tools/actions for the agent
- **State**: ENABLED
- **Tools**: 5 security-focused functions
- **Schema**: OpenAPI or Function Details

### **Layer 6: Security Lambda**
- **Purpose**: Execute security checks and AWS API calls
- **Runtime**: Python 3.9
- **Role**: GatewayProxyLambdaRole
- **Integration**: Direct AWS SDK calls

### **Layer 7: AWS Security Services**
- **Purpose**: Actual security data sources
- **Services**: GuardDuty, Security Hub, S3, EC2, etc.
- **Access**: Via AWS SDK with IAM permissions

### **Layer 8: AgentCore Gateway**
- **Purpose**: MCP (Model Context Protocol) server
- **Authentication**: OAuth 2.0 with Cognito
- **Tools**: 6 security tools with MCP prefix
- **Protocol**: MCP over HTTPS

### **Layer 9: AgentCore Runtime**
- **Purpose**: Container-based agent hosting
- **Deployment**: Managed containers
- **Features**: Memory, Code Interpreter, Observability

## Data Flow

### Request Flow (User → Response)
```
1. User types message in React UI
2. React sends POST to API Gateway /chat endpoint
3. API Gateway triggers Web API Lambda
4. Web API Lambda calls bedrock-agent-runtime:InvokeAgent
5. Bedrock Agent analyzes request with Claude 3 Haiku
6. Agent decides which action to invoke
7. Agent calls Action Group Lambda (bedrock-gateway-proxy)
8. Security Lambda makes AWS API calls (GuardDuty, Security Hub, etc.)
9. Security Lambda returns results to Agent
10. Agent synthesizes response
11. Response flows back through Web API Lambda
12. API Gateway returns response to React UI
13. User sees response in chat interface
```

### Response Format
```json
{
  "response": "Security analysis results...",
  "sessionId": "unique-session-id",
  "trace": {
    "rationale": "Agent's reasoning",
    "actions": ["actions taken"],
    "observations": ["results observed"]
  }
}
```

## Key Design Decisions

### Why This Architecture?

1. **Separation of Concerns**
   - Frontend handles UI/UX
   - API Gateway handles HTTP routing
   - Web API Lambda handles agent invocation
   - Bedrock Agent handles AI orchestration
   - Security Lambda handles AWS API calls

2. **Scalability**
   - S3 scales automatically for static content
   - API Gateway scales automatically
   - Lambda scales automatically
   - Bedrock Agent is fully managed

3. **Security**
   - S3 bucket policy controls frontend access
   - API Gateway can add authentication
   - IAM roles control Lambda permissions
   - Bedrock Agent has its own service role

4. **Cost Optimization**
   - S3 hosting is cheap
   - API Gateway pay-per-request
   - Lambda pay-per-invocation
   - Claude 3 Haiku is cost-effective

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React | Latest | UI Framework |
| Hosting | S3 | - | Static Website |
| API | API Gateway | REST | HTTP Endpoint |
| Compute | Lambda | Python 3.9 | Serverless Functions |
| AI | Bedrock Agent | - | Agent Orchestration |
| Model | Claude 3 Haiku | v1:0 | LLM |
| Security | GuardDuty, Security Hub | - | Security Data |
| AgentCore | Gateway + Runtime | - | MCP Tools |

## Region Configuration

- **Primary Region**: us-east-1
- **All Resources**: Must be in same region
- **Bedrock Model Access**: Must be enabled in region

## IAM Roles

### GatewayProxyLambdaRole
Used by both:
- Web API Lambda (chatbot-web-api)
- Security Lambda (bedrock-gateway-proxy)

**Required Permissions**:
- `bedrock:InvokeAgent` (for Web API Lambda)
- `guardduty:*` (for Security Lambda)
- `securityhub:*` (for Security Lambda)
- `s3:*` (for Security Lambda)
- `ec2:Describe*` (for Security Lambda)
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

## Next Steps

Each layer has its own detailed documentation:
- [Layer 1: S3 Frontend](./01-S3-FRONTEND.md)
- [Layer 2: API Gateway](./02-API-GATEWAY.md)
- [Layer 3: Web API Lambda](./03-WEB-API-LAMBDA.md)
- [Layer 4: Bedrock Agent](./04-BEDROCK-AGENT.md)
- [Layer 5: Action Group](./05-ACTION-GROUP.md)
- [Layer 6: Security Lambda](./06-SECURITY-LAMBDA.md)
- [Layer 7: AWS Services](./07-AWS-SERVICES.md)
- [Layer 8: AgentCore Gateway](./08-AGENTCORE-GATEWAY.md)
- [Layer 9: AgentCore Runtime](./09-AGENTCORE-RUNTIME.md)
