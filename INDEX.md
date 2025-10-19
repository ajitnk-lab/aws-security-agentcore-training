# Complete Knowledge Base - Multi-Layer Bedrock Agent Architecture

## 🚨 START HERE - ISSUES & SOLUTIONS

**If you're facing issues, read this first:**
- [**ALL ISSUES & SOLUTIONS**](wikis/ALL-ISSUES-AND-SOLUTIONS.md) - Complete reference of every issue and fix
- [**DependencyFailedException Guide**](wikis/BEDROCK-AGENT-DEPENDENCY-FAILED-EXCEPTION.md) - Most common error
- [**Troubleshooting Workflow**](wikis/AGENT-TROUBLESHOOTING-WORKFLOW.md) - Systematic debugging

---

## 📚 Documentation Structure

This knowledge base contains everything you need to build, deploy, and maintain a multi-layer Bedrock Agent application.

---

## 🎯 Quick Start

1. **Start Here**: [Architecture Overview](./wikis/00-ARCHITECTURE-OVERVIEW.md)
2. **Your Flow**: [DEPLOYMENT_FLOW.md](./DEPLOYMENT_FLOW.md)
3. **Build Guide**: Follow layer-by-layer guides below

---

## 📖 Layer-by-Layer Guides

### Frontend & API Layers
- **[Layer 1: S3 Static Website](./wikis/01-S3-FRONTEND.md)**
  - React app deployment
  - S3 bucket configuration
  - CORS setup
  - Security considerations
  - Common pitfalls

- **[Layer 2: API Gateway](./wikis/02-API-GATEWAY.md)**
  - REST API setup
  - Lambda proxy integration
  - CORS configuration
  - Throttling and quotas
  - Error handling

- **[Layer 3: Web API Lambda](./wikis/03-WEB-API-LAMBDA.md)**
  - Lambda function structure
  - Bedrock Agent invocation
  - Session management
  - Error handling
  - Cold start optimization

### AI & Orchestration Layers
- **[Layer 4: Bedrock Agent](./wikis/04-BEDROCK-AGENT.md)**
  - Agent creation and configuration
  - Model selection (Claude 3 Haiku)
  - Instructions and prompts
  - Preparing and deploying
  - Testing and debugging

- **[Layer 5: Action Group](./wikis/05-ACTION-GROUP.md)**
  - OpenAPI schema design
  - Function definitions
  - Parameter handling
  - Lambda integration
  - Best practices

- **[Layer 6: Security Lambda](./wikis/06-SECURITY-LAMBDA.md)**
  - Lambda function structure
  - AWS SDK integration
  - Security service calls
  - Response formatting
  - Error handling

### Data & Advanced Layers
- **[Layer 7: AWS Security Services](./wikis/07-AWS-SERVICES.md)**
  - GuardDuty integration
  - Security Hub queries
  - S3 security checks
  - EC2 security analysis
  - IAM permissions

- **[Layer 8: AgentCore Gateway](./wikis/08-AGENTCORE-GATEWAY.md)**
  - MCP server setup
  - OAuth authentication
  - Tool registration
  - Lambda targets
  - OpenAPI targets

- **[Layer 9: AgentCore Runtime](./wikis/09-AGENTCORE-RUNTIME.md)**
  - Container deployment
  - Memory integration
  - Code Interpreter
  - Observability
  - Best practices

---

## 🔧 How-To Guides

### Deployment
- **[Complete Deployment Guide](./how-to/COMPLETE-DEPLOYMENT.md)**
  - Step-by-step deployment
  - Prerequisites
  - Configuration
  - Testing
  - Troubleshooting

### Development
- **[Local Development Setup](./how-to/LOCAL-DEVELOPMENT.md)**
  - Development environment
  - Testing locally
  - Debugging techniques
  - Hot reload setup

### Operations
- **[Monitoring & Logging](./how-to/MONITORING.md)**
  - CloudWatch setup
  - Log analysis
  - Performance metrics
  - Alerting

- **[Security Best Practices](./how-to/SECURITY.md)**
  - IAM roles and policies
  - Encryption
  - Network security
  - Compliance

---

## ⚠️ Pitfalls & Solutions

### Common Pitfalls
- **[S3 & Frontend Pitfalls](./pitfalls/S3-PITFALLS.md)**
- **[API Gateway Pitfalls](./pitfalls/API-GATEWAY-PITFALLS.md)**
- **[Lambda Pitfalls](./pitfalls/LAMBDA-PITFALLS.md)**
- **[Bedrock Agent Pitfalls](./pitfalls/BEDROCK-AGENT-PITFALLS.md)**
- **[Action Group Pitfalls](./pitfalls/ACTION-GROUP-PITFALLS.md)**
- **[IAM & Permissions Pitfalls](./pitfalls/IAM-PITFALLS.md)**
- **[AgentCore Pitfalls](./pitfalls/AGENTCORE-PITFALLS.md)**

---

## 📝 Reference Documentation

### Code Examples
- **[Complete Code Examples](./examples/)**
  - React frontend code
  - Lambda function templates
  - Action group schemas
  - IAM policy templates
  - CloudFormation templates

### API Reference
- **[Bedrock Agent APIs](./reference/BEDROCK-AGENT-API.md)**
- **[AgentCore APIs](./reference/AGENTCORE-API.md)**
- **[Lambda Event Formats](./reference/LAMBDA-EVENTS.md)**

### Configuration Templates
- **[IAM Policies](./reference/IAM-POLICIES.md)**
- **[OpenAPI Schemas](./reference/OPENAPI-SCHEMAS.md)**
- **[Environment Variables](./reference/ENVIRONMENT-VARS.md)**

---

## 🎓 Tutorials

### Beginner
- **[Tutorial 1: Build Your First Agent](./tutorials/01-FIRST-AGENT.md)**
- **[Tutorial 2: Add Action Groups](./tutorials/02-ACTION-GROUPS.md)**
- **[Tutorial 3: Deploy to Production](./tutorials/03-PRODUCTION-DEPLOY.md)**

### Intermediate
- **[Tutorial 4: Add AgentCore Gateway](./tutorials/04-AGENTCORE-GATEWAY.md)**
- **[Tutorial 5: Implement Memory](./tutorials/05-MEMORY.md)**
- **[Tutorial 6: Advanced Observability](./tutorials/06-OBSERVABILITY.md)**

### Advanced
- **[Tutorial 7: Multi-Agent Systems](./tutorials/07-MULTI-AGENT.md)**
- **[Tutorial 8: Custom Frameworks](./tutorials/08-CUSTOM-FRAMEWORKS.md)**
- **[Tutorial 9: Production Optimization](./tutorials/09-OPTIMIZATION.md)**

---

## 🔍 Troubleshooting

### By Symptom
- **[Agent Not Responding](./troubleshooting/AGENT-NOT-RESPONDING.md)**
- **[Lambda Timeouts](./troubleshooting/LAMBDA-TIMEOUTS.md)**
- **[Permission Errors](./troubleshooting/PERMISSION-ERRORS.md)**
- **[CORS Issues](./troubleshooting/CORS-ISSUES.md)**
- **[Cold Start Problems](./troubleshooting/COLD-STARTS.md)**

### By Component
- **[S3 Troubleshooting](./troubleshooting/S3-ISSUES.md)**
- **[API Gateway Troubleshooting](./troubleshooting/API-GATEWAY-ISSUES.md)**
- **[Lambda Troubleshooting](./troubleshooting/LAMBDA-ISSUES.md)**
- **[Bedrock Agent Troubleshooting](./troubleshooting/BEDROCK-AGENT-ISSUES.md)**
- **[AgentCore Troubleshooting](./troubleshooting/AGENTCORE-ISSUES.md)**

---

## 📊 Architecture Patterns

- **[Pattern 1: Simple Agent](./patterns/SIMPLE-AGENT.md)**
- **[Pattern 2: Multi-Tool Agent](./patterns/MULTI-TOOL-AGENT.md)**
- **[Pattern 3: AgentCore Integration](./patterns/AGENTCORE-INTEGRATION.md)**
- **[Pattern 4: Hybrid Approach](./patterns/HYBRID-APPROACH.md)**

---

## 🚀 Next Steps

### For New Projects
1. Read [Architecture Overview](./wikis/00-ARCHITECTURE-OVERVIEW.md)
2. Follow [Complete Deployment Guide](./how-to/COMPLETE-DEPLOYMENT.md)
3. Review [Common Pitfalls](./pitfalls/)
4. Build your first agent with [Tutorial 1](./tutorials/01-FIRST-AGENT.md)

### For Existing Projects
1. Review your current architecture against [Architecture Overview](./wikis/00-ARCHITECTURE-OVERVIEW.md)
2. Check [Pitfalls](./pitfalls/) for issues you might be facing
3. Optimize using [Production Optimization](./tutorials/09-OPTIMIZATION.md)
4. Consider [AgentCore Integration](./patterns/AGENTCORE-INTEGRATION.md)

---

## 📚 External Resources

### AWS Documentation
- [Amazon Bedrock Agents User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Amazon Bedrock AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/latest/dg/)
- [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/)

### Community Resources
- [AgentCore Starter Toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)
- [AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples)
- [AWS Samples](https://github.com/aws-samples)

---

## 🤝 Contributing

This knowledge base is built from real-world experience. As you build your solution:
1. Document new pitfalls you discover
2. Add solutions that worked for you
3. Share optimization techniques
4. Update with new AWS features

---

## 📅 Last Updated

This knowledge base was created on: 2025-10-19

**Note**: AWS services evolve rapidly. Always check official AWS documentation for the latest features and best practices.
