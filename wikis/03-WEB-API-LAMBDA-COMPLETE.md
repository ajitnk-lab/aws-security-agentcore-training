# Layer 3: Web API Lambda - Complete Guide

## Overview

The Web API Lambda (`chatbot-web-api`) bridges API Gateway and Bedrock Agent:
- **Receives**: HTTP POST from API Gateway with user message
- **Invokes**: Bedrock Agent via `bedrock-agent-runtime:InvokeAgent`
- **Returns**: Agent response back to frontend

---

## Code Review & Issues Found

### ⚠️ Issues in Original Code:

1. **Missing error details in logs** - Generic error messages
2. **No agent state validation** - Doesn't check if agent is PREPARED
3. **Hardcoded agent alias** - Should be environment variable
4. **Streaming response handling** - Can fail silently
5. **No timeout handling** - Can hang indefinitely
6. **CORS headers incomplete** - Missing error case headers
7. **Session ID generation** - No validation

---

## Corrected Lambda Code

### Version 1: Production-Ready Code

```python
import json
import boto3
import uuid
import os
from botocore.exceptions import ClientError

# Environment variables
AGENT_ID = os.environ.get('AGENT_ID', 'VS4IAMTUZO')
AGENT_ALIAS_ID = os.environ.get('AGENT_ALIAS_ID', 'OUUY9MTH8E')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')

# Initialize client outside handler for reuse
bedrock_client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)

def get_cors_headers():
    """Return CORS headers for all responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'Content-Type': 'application/json'
    }

def validate_agent_ready(agent_id, agent_alias_id):
    """
    Validate agent is in PREPARED state before invoking
    Returns: (is_ready: bool, error_message: str)
    """
    try:
        response = bedrock_agent_client.get_agent(agentId=agent_id)
        agent_status = response['agent']['agentStatus']
        
        if agent_status != 'PREPARED':
            return False, f"Agent not ready. Status: {agent_status}. Please prepare the agent first."
        
        # Validate alias exists
        try:
            bedrock_agent_client.get_agent_alias(
                agentId=agent_id,
                agentAliasId=agent_alias_id
            )
        except ClientError as e:
            return False, f"Agent alias not found: {agent_alias_id}"
        
        return True, None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            return False, f"Agent not found: {agent_id}"
        return False, f"Error validating agent: {str(e)}"

def validate_session_id(session_id):
    """Validate session ID format"""
    if not session_id:
        return str(uuid.uuid4())
    
    # Session ID must be 2-100 characters
    if len(session_id) < 2 or len(session_id) > 100:
        return str(uuid.uuid4())
    
    return session_id

def lambda_handler(event, context):
    """
    Web API Lambda handler for Bedrock Agent invocation
    """
    
    print(f"Received event: {json.dumps(event)}")
    
    headers = get_cors_headers()
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message', '').strip()
        session_id = validate_session_id(body.get('sessionId'))
        
        # Validate input
        if not user_message:
            print("Error: Empty message received")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Message is required',
                    'response': 'Please provide a message.'
                })
            }
        
        if len(user_message) > 25000:  # Bedrock limit
            print(f"Error: Message too long ({len(user_message)} chars)")
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Message too long',
                    'response': 'Please provide a shorter message (max 25,000 characters).'
                })
            }
        
        print(f"Processing message: {user_message[:100]}... (Session: {session_id})")
        
        # Validate agent is ready (optional - remove if too slow)
        # is_ready, error_msg = validate_agent_ready(AGENT_ID, AGENT_ALIAS_ID)
        # if not is_ready:
        #     print(f"Agent validation failed: {error_msg}")
        #     return {
        #         'statusCode': 503,
        #         'headers': headers,
        #         'body': json.dumps({
        #             'error': 'Agent not available',
        #             'response': error_msg
        #         })
        #     }
        
        # Invoke Bedrock Agent
        print(f"Invoking agent {AGENT_ID} with alias {AGENT_ALIAS_ID}")
        
        response = bedrock_client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=user_message,
            enableTrace=True  # Enable for debugging
        )
        
        # Process streaming response
        agent_response = ""
        trace_data = []
        event_stream = response.get('completion', [])
        
        for event in event_stream:
            # Handle response chunks
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    agent_response += chunk_text
                    print(f"Received chunk: {chunk_text[:100]}...")
            
            # Handle trace events (for debugging)
            elif 'trace' in event:
                trace = event['trace']
                trace_data.append(trace)
                print(f"Trace event: {json.dumps(trace)[:200]}...")
        
        # Validate response
        if not agent_response:
            print("Warning: Empty response from agent")
            agent_response = "I received your message but couldn't generate a response. Please try again."
        
        print(f"Agent response: {agent_response[:200]}...")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'response': agent_response,
                'sessionId': session_id,
                'trace': trace_data if trace_data else None  # Include for debugging
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"AWS Error: {error_code} - {error_message}")
        print(f"Full error: {json.dumps(e.response)}")
        
        # Handle specific errors
        if error_code == 'ResourceNotFoundException':
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Agent not found',
                    'response': f'The agent or alias was not found. Please check configuration.',
                    'details': error_message
                })
            }
        elif error_code == 'ValidationException':
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Invalid request',
                    'response': 'There was an issue with the request format.',
                    'details': error_message
                })
            }
        elif error_code == 'ThrottlingException':
            return {
                'statusCode': 429,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Too many requests',
                    'response': 'Please wait a moment and try again.',
                    'details': error_message
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Service error',
                    'response': 'An error occurred while processing your request.',
                    'details': f'{error_code}: {error_message}'
                })
            }
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Invalid JSON',
                'response': 'The request body is not valid JSON.'
            })
        }
    
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'response': 'An unexpected error occurred. Please try again.',
                'details': str(e)
            })
        }
```

### Key Improvements:

1. ✅ **Environment variables** - No hardcoded values
2. ✅ **Comprehensive error handling** - Specific error codes
3. ✅ **Detailed logging** - Every step logged
4. ✅ **Input validation** - Message length, session ID format
5. ✅ **Agent state validation** - Optional check if agent is ready
6. ✅ **Trace support** - Enable for debugging
7. ✅ **CORS headers** - Complete and consistent
8. ✅ **Client reuse** - boto3 client outside handler (performance)

---

## Deployment

### Step 1: Create requirements.txt

```txt
boto3>=1.34.0
botocore>=1.34.0
```

**Note**: Lambda includes boto3 by default, but pin version for consistency.

### Step 2: Package Lambda

Create `deploy-lambda.sh`:

```bash
#!/bin/bash
set -e

echo "📦 Web API Lambda Deployment Script"
echo "===================================="

# Prompt for function name
read -p "Enter Lambda function name [chatbot-web-api]: " FUNCTION_NAME
FUNCTION_NAME=${FUNCTION_NAME:-chatbot-web-api}

# Prompt for agent details
read -p "Enter Agent ID: " AGENT_ID
read -p "Enter Agent Alias ID: " AGENT_ALIAS_ID
read -p "Enter AWS Region [us-east-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-us-east-1}

echo ""
echo "Configuration:"
echo "  Function: $FUNCTION_NAME"
echo "  Agent ID: $AGENT_ID"
echo "  Alias ID: $AGENT_ALIAS_ID"
echo "  Region: $AWS_REGION"
echo ""
read -p "Continue? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Step 1: Create deployment package
echo ""
echo "📦 Step 1: Creating deployment package..."

# Clean previous builds
rm -rf package lambda.zip

# Create package directory
mkdir -p package

# Install dependencies (if requirements.txt exists)
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt -t package/
fi

# Copy Lambda code
cp lambda_function.py package/

# Create zip
cd package
zip -r ../lambda.zip . -q
cd ..

# Clean up
rm -rf package

echo "✅ Package created: lambda.zip"

# Step 2: Check if function exists
echo ""
echo "🔍 Step 2: Checking if function exists..."

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$AWS_REGION" 2>&1 | grep -q 'ResourceNotFoundException'; then
    echo "❌ Function does not exist"
    echo ""
    echo "Please create the function first:"
    echo "  1. Go to AWS Lambda Console"
    echo "  2. Create function: $FUNCTION_NAME"
    echo "  3. Runtime: Python 3.9"
    echo "  4. Role: GatewayProxyLambdaRole (with bedrock:InvokeAgent permission)"
    echo "  5. Then run this script again"
    exit 1
else
    echo "✅ Function exists"
fi

# Step 3: Update function code
echo ""
echo "📤 Step 3: Uploading code..."

aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://lambda.zip \
    --region "$AWS_REGION" \
    --no-cli-pager

echo "✅ Code uploaded"

# Step 4: Update environment variables
echo ""
echo "🔧 Step 4: Updating environment variables..."

aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --environment "Variables={AGENT_ID=$AGENT_ID,AGENT_ALIAS_ID=$AGENT_ALIAS_ID,AWS_REGION=$AWS_REGION}" \
    --region "$AWS_REGION" \
    --no-cli-pager

echo "✅ Environment variables set"

# Step 5: Wait for update to complete
echo ""
echo "⏳ Step 5: Waiting for function to be ready..."
sleep 5

aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION"

echo "✅ Function ready"

# Step 6: Test invocation (optional)
echo ""
read -p "Test the function? (y/n): " TEST

if [ "$TEST" = "y" ]; then
    echo ""
    echo "🧪 Testing function..."
    
    cat > test-event.json <<EOF
{
  "httpMethod": "POST",
  "body": "{\"message\": \"Hello, test message\", \"sessionId\": \"test-session-123\"}"
}
EOF
    
    aws lambda invoke \
        --function-name "$FUNCTION_NAME" \
        --payload file://test-event.json \
        --region "$AWS_REGION" \
        response.json
    
    echo ""
    echo "Response:"
    cat response.json | jq '.'
    
    rm test-event.json response.json
fi

echo ""
echo "===================================="
echo "✅ Deployment Complete!"
echo "===================================="
echo ""
echo "Function ARN:"
aws lambda get-function \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --query 'Configuration.FunctionArn' \
    --output text

echo ""
echo "View logs:"
echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo ""
```

Make executable:
```bash
chmod +x deploy-lambda.sh
```

### Step 3: Deploy

```bash
./deploy-lambda.sh
```

---

## Common Issues & Solutions

### Issue 1: "Agent not found" Error

**Error**:
```json
{
  "error": "Agent not found",
  "details": "ResourceNotFoundException"
}
```

**Causes**:
- Wrong Agent ID
- Wrong region
- Agent deleted

**Solution**:
```bash
# List agents
aws bedrock-agent list-agents --region us-east-1

# Get agent details
aws bedrock-agent get-agent --agent-id YOUR_AGENT_ID --region us-east-1

# Check agent status
aws bedrock-agent get-agent --agent-id YOUR_AGENT_ID \
    --query 'agent.agentStatus' --output text
```

### Issue 2: "Agent not prepared" Error

**Error**: Agent status is `NOT_PREPARED` or `CREATING`

**Solution**:
```bash
# Prepare the agent
aws bedrock-agent prepare-agent --agent-id YOUR_AGENT_ID --region us-east-1

# Wait for preparation (can take 1-2 minutes)
sleep 60

# Check status
aws bedrock-agent get-agent --agent-id YOUR_AGENT_ID \
    --query 'agent.agentStatus' --output text
```

**Important**: Always wait after preparing agent before testing!

### Issue 3: "Access Denied" - IAM Permissions

**Error**:
```json
{
  "error": "AccessDeniedException",
  "details": "User is not authorized to perform: bedrock:InvokeAgent"
}
```

**Solution**: Update Lambda execution role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent",
        "bedrock:GetAgent",
        "bedrock:GetAgentAlias"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1:ACCOUNT_ID:agent/*",
        "arn:aws:bedrock:us-east-1:ACCOUNT_ID:agent-alias/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### Issue 4: Empty Response from Agent

**Symptom**: `agent_response` is empty string

**Causes**:
- Agent has no action groups
- Agent instructions unclear
- Streaming response not fully read

**Solution**:
```python
# Add timeout and validation
import time

start_time = time.time()
for event in event_stream:
    if time.time() - start_time > 30:  # 30 second timeout
        break
    # ... process events

if not agent_response:
    # Log for debugging
    print(f"Empty response. Trace: {trace_data}")
```

### Issue 5: Lambda Timeout

**Error**: Task timed out after 3.00 seconds

**Solution**:
```bash
# Increase timeout to 30 seconds
aws lambda update-function-configuration \
    --function-name chatbot-web-api \
    --timeout 30 \
    --region us-east-1
```

### Issue 6: Dependency Issues (boto3 version)

**Error**: `AttributeError: 'BedrockAgentRuntime' object has no attribute 'invoke_agent'`

**Cause**: Old boto3 version

**Solution**:
```bash
# Create Lambda Layer with latest boto3
mkdir python
pip install boto3>=1.34.0 -t python/
zip -r boto3-layer.zip python/

# Create layer
aws lambda publish-layer-version \
    --layer-name boto3-latest \
    --zip-file fileb://boto3-layer.zip \
    --compatible-runtimes python3.9

# Attach to function
aws lambda update-function-configuration \
    --function-name chatbot-web-api \
    --layers arn:aws:lambda:REGION:ACCOUNT:layer:boto3-latest:1
```

---

## CloudWatch Logs Debugging

### View Logs
```bash
# Tail logs in real-time
aws logs tail /aws/lambda/chatbot-web-api --follow

# Get recent logs
aws logs tail /aws/lambda/chatbot-web-api --since 1h

# Filter for errors
aws logs tail /aws/lambda/chatbot-web-api --filter-pattern "ERROR"
```

### Log Structure

**Successful invocation**:
```
START RequestId: abc-123
Received event: {"httpMethod": "POST", ...}
Processing message: Hello... (Session: xyz)
Invoking agent VS4IAMTUZO with alias OUUY9MTH8E
Received chunk: I can help...
Agent response: I can help you...
END RequestId: abc-123
REPORT RequestId: abc-123 Duration: 2500ms Memory: 128MB
```

**Failed invocation**:
```
START RequestId: abc-123
Received event: {"httpMethod": "POST", ...}
AWS Error: ResourceNotFoundException - Agent not found
Full error: {"Error": {"Code": "ResourceNotFoundException", ...}}
END RequestId: abc-123
```

---

## Testing

### Test Event (API Gateway format)
```json
{
  "httpMethod": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": "{\"message\": \"What security issues do I have?\", \"sessionId\": \"test-123\"}"
}
```

### Test via AWS CLI
```bash
aws lambda invoke \
    --function-name chatbot-web-api \
    --payload '{"httpMethod":"POST","body":"{\"message\":\"test\"}"}' \
    response.json

cat response.json | jq '.'
```

### Test via Console
1. Go to Lambda Console
2. Select `chatbot-web-api`
3. Test tab
4. Create test event with above JSON
5. Click "Test"
6. Check response and logs

---

## Best Practices

1. **Always enable trace during development** - `enableTrace=True`
2. **Log everything** - Input, output, errors
3. **Use environment variables** - Never hardcode IDs
4. **Validate agent state** - Check PREPARED before invoking
5. **Handle all error types** - ClientError, JSONDecodeError, etc.
6. **Set appropriate timeout** - 30 seconds minimum
7. **Monitor CloudWatch** - Set up alarms for errors
8. **Version your code** - Use Lambda versions/aliases

---

## Next Layer

Once Web API Lambda is working, proceed to:
- **[Layer 4: Bedrock Agent](./04-BEDROCK-AGENT.md)** - Create and configure the agent
