"""
Complete Parameter Mapping Solution
Handles all parameter transformations from Bedrock Agent to Gateway tools
"""
import json

# Step 1: Define Gateway tool signatures
GATEWAY_TOOL_SIGNATURES = {
    'SecurityMCPTools___CheckSecurityServices': {
        'parameters': {
            'region': {'type': 'string', 'required': True, 'default': 'us-east-1'},
            'service_names': {'type': 'array', 'required': False, 'default': []},
        }
    },
    'SecurityMCPTools___GetSecurityFindings': {
        'parameters': {
            'region': {'type': 'string', 'required': True, 'default': 'us-east-1'},
            'severity': {'type': 'string', 'required': False, 'default': 'ALL'},
            'service': {'type': 'string', 'required': False, 'default': None},
            'limit': {'type': 'integer', 'required': False, 'default': 100},
        }
    },
    'SecurityMCPTools___CheckStorageEncryption': {
        'parameters': {
            'region': {'type': 'string', 'required': True, 'default': 'us-east-1'},
            'service_type': {'type': 'string', 'required': False, 'default': 'ALL'},
        }
    },
}

# Step 2: Map action group operations to Gateway tools
OPERATION_TO_TOOL_MAP = {
    'checkSecurityStatus': 'SecurityMCPTools___CheckSecurityServices',
    'getSecurityFindings': 'SecurityMCPTools___GetSecurityFindings',
    'checkStorageEncryption': 'SecurityMCPTools___CheckStorageEncryption',
    # Add all your operations here
}

# Step 3: Map Bedrock parameter names to Gateway parameter names
PARAMETER_NAME_MAP = {
    'SecurityMCPTools___CheckSecurityServices': {
        'region': 'region',
        'service': 'service_names',  # Note: singular to plural, string to array
        'services': 'service_names',
    },
    'SecurityMCPTools___GetSecurityFindings': {
        'region': 'region',
        'severity': 'severity',  # Direct mapping
        'service': 'service',
        'limit': 'limit',
    },
    'SecurityMCPTools___CheckStorageEncryption': {
        'region': 'region',
        'serviceType': 'service_type',  # camelCase to snake_case
        'service_type': 'service_type',
    },
}


def map_parameters(operation_id, bedrock_parameters):
    """
    Map Bedrock Agent parameters to Gateway tool parameters
    
    Args:
        operation_id: Action group operation ID (e.g., 'checkSecurityStatus')
        bedrock_parameters: List of {name, type, value} from Bedrock event
    
    Returns:
        dict: Mapped parameters ready for Gateway tool call
    """
    
    # Get Gateway tool name
    tool_name = OPERATION_TO_TOOL_MAP.get(operation_id)
    if not tool_name:
        raise ValueError(f"Unknown operation: {operation_id}")
    
    # Get tool signature
    tool_sig = GATEWAY_TOOL_SIGNATURES.get(tool_name)
    if not tool_sig:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    # Get parameter name mapping for this tool
    param_map = PARAMETER_NAME_MAP.get(tool_name, {})
    
    # Start with default values
    mapped_params = {}
    for param_name, param_def in tool_sig['parameters'].items():
        if param_def.get('default') is not None:
            mapped_params[param_name] = param_def['default']
    
    # Map provided parameters
    for bedrock_param in bedrock_parameters:
        bedrock_name = bedrock_param.get('name')
        bedrock_value = bedrock_param.get('value')
        
        # Get mapped name
        gateway_name = param_map.get(bedrock_name, bedrock_name)
        
        # Get expected type
        param_def = tool_sig['parameters'].get(gateway_name, {})
        expected_type = param_def.get('type', 'string')
        
        # Convert value to expected type
        if expected_type == 'array':
            # Convert single value to array
            if isinstance(bedrock_value, list):
                mapped_params[gateway_name] = bedrock_value
            else:
                mapped_params[gateway_name] = [bedrock_value]
        
        elif expected_type == 'integer':
            mapped_params[gateway_name] = int(bedrock_value)
        
        elif expected_type == 'boolean':
            if isinstance(bedrock_value, str):
                mapped_params[gateway_name] = bedrock_value.lower() in ['true', '1', 'yes']
            else:
                mapped_params[gateway_name] = bool(bedrock_value)
        
        else:  # string
            mapped_params[gateway_name] = str(bedrock_value)
    
    # Validate required parameters
    for param_name, param_def in tool_sig['parameters'].items():
        if param_def.get('required') and param_name not in mapped_params:
            raise ValueError(f"Missing required parameter: {param_name}")
    
    return tool_name, mapped_params


def lambda_handler(event, context):
    """Example usage in Lambda"""
    
    operation_id = event.get('actionGroup', '')
    bedrock_parameters = event.get('parameters', [])
    
    print(f"Operation: {operation_id}")
    print(f"Bedrock Parameters: {json.dumps(bedrock_parameters, indent=2)}")
    
    try:
        # Map parameters
        tool_name, mapped_params = map_parameters(operation_id, bedrock_parameters)
        
        print(f"Gateway Tool: {tool_name}")
        print(f"Mapped Parameters: {json.dumps(mapped_params, indent=2)}")
        
        # Build MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": mapped_params
            }
        }
        
        # Call Gateway...
        # (rest of your code)
        
    except ValueError as e:
        print(f"Parameter mapping error: {e}")
        return error_response(event, str(e))


# Example test cases
if __name__ == '__main__':
    # Test 1: Check security status
    print("Test 1: Check security status")
    bedrock_params = [
        {'name': 'region', 'type': 'string', 'value': 'us-east-1'},
        {'name': 'service', 'type': 'string', 'value': 'EC2'}
    ]
    tool_name, mapped = map_parameters('checkSecurityStatus', bedrock_params)
    print(f"  Tool: {tool_name}")
    print(f"  Params: {mapped}")
    print()
    
    # Test 2: Get security findings
    print("Test 2: Get security findings")
    bedrock_params = [
        {'name': 'region', 'type': 'string', 'value': 'us-west-2'},
        {'name': 'severity', 'type': 'string', 'value': 'HIGH'},
        {'name': 'limit', 'type': 'string', 'value': '50'}
    ]
    tool_name, mapped = map_parameters('getSecurityFindings', bedrock_params)
    print(f"  Tool: {tool_name}")
    print(f"  Params: {mapped}")
    print()
    
    # Test 3: Missing optional parameter (should use default)
    print("Test 3: Missing optional parameter")
    bedrock_params = [
        {'name': 'region', 'type': 'string', 'value': 'eu-west-1'}
    ]
    tool_name, mapped = map_parameters('getSecurityFindings', bedrock_params)
    print(f"  Tool: {tool_name}")
    print(f"  Params: {mapped}")
    print(f"  Note: severity defaulted to {mapped['severity']}")
