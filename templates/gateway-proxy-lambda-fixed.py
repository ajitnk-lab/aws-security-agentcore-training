import json
import os
import requests
import base64

def lambda_handler(event, context):
    """
    Action Group Target Lambda: Bedrock Agent -> AgentCore Gateway
    FIXED VERSION with proper response format
    """
    
    # Environment variables (set these in Lambda config)
    gateway_url = os.environ.get('GATEWAY_URL', 'https://security-chatbot-gateway-41f3cc60-fmqz5lmy6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp')
    client_id = os.environ.get('COGNITO_CLIENT_ID', '6aarhftf6bopppar05humcp2r6')
    client_secret = os.environ.get('COGNITO_CLIENT_SECRET', '')
    token_url = os.environ.get('TOKEN_URL', 'https://security-chatbot-oauth-domain.auth.us-east-1.amazoncognito.com/oauth2/token')
    
    # Validate event structure
    if 'actionGroup' not in event:
        return error_response(event, 'Missing actionGroup in event')
    
    try:
        # Get OAuth token
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        token_response = requests.post(
            token_url,
            headers={
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data='grant_type=client_credentials',
            timeout=10
        )
        
        if token_response.status_code != 200:
            print(f"Token request failed: {token_response.status_code} - {token_response.text}")
            return error_response(event, f"Failed to get OAuth token: {token_response.status_code}")
        
        token = token_response.json()['access_token']
        
        # Extract parameters
        operation_id = event.get('actionGroup', '')
        parameters = event.get('parameters', [])
        
        print(f"Operation: {operation_id}")
        print(f"Parameters: {parameters}")
        
        # Convert to MCP format
        mcp_params = {}
        for param in parameters:
            param_name = param.get('name')
            param_value = param.get('value')
            
            if param_name == 'region':
                mcp_params['region'] = param_value
            elif param_name == 'severity':
                mcp_params['severity_filter'] = param_value
            elif param_name == 'service':
                mcp_params['services'] = [param_value]
        
        # Map to MCP tool name
        tool_name_map = {
            'get_security_status': 'SecurityMCPTools___CheckSecurityServices',
            'get_security_findings': 'SecurityMCPTools___GetSecurityFindings',
            'check_storage_encryption': 'SecurityMCPTools___CheckStorageEncryption',
            'list_services_in_region': 'SecurityMCPTools___ListServicesInRegion',
            'check_network_security': 'SecurityMCPTools___CheckNetworkSecurity'
        }
        
        mcp_tool_name = tool_name_map.get(operation_id, f'SecurityMCPTools___{operation_id}')
        
        # Build MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": mcp_tool_name,
                "arguments": mcp_params
            }
        }
        
        print(f"MCP Request: {json.dumps(mcp_request, indent=2)}")
        
        # Call Gateway
        response = requests.post(
            gateway_url,
            json=mcp_request,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
        
        print(f"Gateway Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Gateway Response: {json.dumps(result, indent=2)}")
            
            mcp_result = result.get('result', {})
            
            # Format result
            if isinstance(mcp_result, dict) and 'resource_details' in mcp_result:
                formatted_result = {
                    'summary': f"Network security analysis for {mcp_result.get('region', 'unknown region')}",
                    'resources_checked': mcp_result.get('resources_checked', 0),
                    'compliant_resources': mcp_result.get('compliant_resources', 0),
                    'non_compliant_resources': mcp_result.get('non_compliant_resources', 0),
                    'compliance_by_service': mcp_result.get('compliance_by_service', {}),
                    'resource_details': mcp_result.get('resource_details', []),
                    'recommendations': mcp_result.get('recommendations', [])
                }
            else:
                formatted_result = mcp_result if isinstance(mcp_result, dict) else {'raw_result': mcp_result}
            
            return success_response(event, formatted_result)
        else:
            error_msg = f'Gateway error: {response.status_code} - {response.text}'
            print(f"Error: {error_msg}")
            return error_response(event, error_msg)
            
    except Exception as e:
        error_msg = f'Lambda error: {str(e)}'
        print(f"Exception: {error_msg}")
        import traceback
        traceback.print_exc()
        return error_response(event, error_msg)


def success_response(event, data):
    """Return properly formatted success response"""
    return {
        'messageVersion': '1.0',  # REQUIRED
        'response': {  # REQUIRED wrapper
            'actionGroup': event.get('actionGroup', ''),
            'apiPath': event.get('apiPath', ''),
            'httpMethod': event.get('httpMethod', ''),
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(data)  # MUST be string
                }
            }
        }
    }


def error_response(event, error_msg):
    """Return properly formatted error response"""
    return {
        'messageVersion': '1.0',  # REQUIRED
        'response': {  # REQUIRED wrapper
            'actionGroup': event.get('actionGroup', ''),
            'apiPath': event.get('apiPath', ''),
            'httpMethod': event.get('httpMethod', ''),
            'httpStatusCode': 500,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'error': error_msg})  # MUST be string
                }
            }
        }
    }
