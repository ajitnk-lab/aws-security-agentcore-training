"""
Bedrock Agent Action Group Lambda - Correct Response Format
"""

def lambda_handler(event, context):
    """
    Target Lambda for Bedrock Agent Action Group
    MUST return specific format or agent invocation fails
    """
    
    # Extract action details
    action_group = event.get('actionGroup', '')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', '')
    parameters = event.get('parameters', [])
    
    # Convert parameters to dict
    params = {p['name']: p['value'] for p in parameters}
    
    # Your business logic here
    result = perform_action(api_path, params)
    
    # CRITICAL: Must return this exact format
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': http_method,
            'httpStatusCode': 200,
            'responseBody': {
                'application/json': {
                    'body': result  # Your actual response data as JSON string
                }
            }
        }
    }


def perform_action(api_path, params):
    """Execute the actual action"""
    
    if api_path == '/check-security-status':
        resource_type = params.get('resourceType', '')
        
        # Your AWS API calls here
        findings = check_security(resource_type)
        
        # Return as JSON STRING, not dict
        import json
        return json.dumps({
            'status': 'success',
            'resourceType': resource_type,
            'findings': findings
        })
    
    return json.dumps({'error': 'Unknown action'})


def check_security(resource_type):
    """Example security check"""
    # Your actual logic here
    return [
        {'severity': 'HIGH', 'description': 'Example finding'}
    ]
