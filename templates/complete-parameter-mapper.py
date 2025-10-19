"""
Complete Parameter Mapping for All Security Tools
Based on actual MCP server tool signatures
"""
import json

# Complete tool signatures from MCP server
GATEWAY_TOOL_SIGNATURES = {
    'SecurityMCPTools___CheckSecurityServices': {
        'parameters': {
            'region': {
                'type': 'string',
                'required': False,
                'default': 'us-east-1',
                'description': 'AWS region to check'
            },
            'services': {
                'type': 'array',
                'required': False,
                'default': ['guardduty', 'inspector', 'accessanalyzer', 'securityhub', 'trustedadvisor', 'macie'],
                'description': 'List of security services to check'
            },
            'account_id': {
                'type': 'string',
                'required': False,
                'default': None,
                'description': 'Optional AWS account ID'
            },
            'aws_profile': {
                'type': 'string',
                'required': False,
                'default': 'default',
                'description': 'AWS profile to use'
            },
            'store_in_context': {
                'type': 'boolean',
                'required': False,
                'default': True,
                'description': 'Store results in context'
            },
            'debug': {
                'type': 'boolean',
                'required': False,
                'default': True,
                'description': 'Include debug information'
            }
        }
    },
    
    'SecurityMCPTools___GetSecurityFindings': {
        'parameters': {
            'region': {
                'type': 'string',
                'required': False,
                'default': 'us-east-1',
                'description': 'AWS region'
            },
            'service': {
                'type': 'string',
                'required': True,
                'default': None,
                'description': 'Security service (guardduty, securityhub, inspector, etc.)'
            },
            'max_findings': {
                'type': 'integer',
                'required': False,
                'default': 100,
                'description': 'Maximum number of findings'
            },
            'severity_filter': {
                'type': 'string',
                'required': False,
                'default': None,
                'description': 'Severity filter (HIGH, CRITICAL, etc.)'
            },
            'aws_profile': {
                'type': 'string',
                'required': False,
                'default': 'default',
                'description': 'AWS profile to use'
            },
            'check_enabled': {
                'type': 'boolean',
                'required': False,
                'default': True,
                'description': 'Check if service is enabled first'
            }
        }
    },
    
    'SecurityMCPTools___CheckStorageEncryption': {
        'parameters': {
            'region': {
                'type': 'string',
                'required': False,
                'default': 'us-east-1',
                'description': 'AWS region'
            },
            'services': {
                'type': 'array',
                'required': False,
                'default': ['s3', 'ebs', 'rds', 'dynamodb', 'efs', 'elasticache'],
                'description': 'Storage services to check'
            },
            'include_unencrypted_only': {
                'type': 'boolean',
                'required': False,
                'default': False,
                'description': 'Show only unencrypted resources'
            },
            'aws_profile': {
                'type': 'string',
                'required': False,
                'default': 'default',
                'description': 'AWS profile to use'
            },
            'store_in_context': {
                'type': 'boolean',
                'required': False,
                'default': True,
                'description': 'Store results in context'
            }
        }
    },
    
    'SecurityMCPTools___CheckNetworkSecurity': {
        'parameters': {
            'region': {
                'type': 'string',
                'required': False,
                'default': 'us-east-1',
                'description': 'AWS region'
            },
            'services': {
                'type': 'array',
                'required': False,
                'default': ['elb', 'vpc', 'apigateway', 'cloudfront'],
                'description': 'Network services to check'
            },
            'include_non_compliant_only': {
                'type': 'boolean',
                'required': False,
                'default': False,
                'description': 'Show only non-compliant resources'
            },
            'aws_profile': {
                'type': 'string',
                'required': False,
                'default': 'default',
                'description': 'AWS profile to use'
            },
            'store_in_context': {
                'type': 'boolean',
                'required': False,
                'default': True,
                'description': 'Store results in context'
            }
        }
    },
    
    'SecurityMCPTools___ListServicesInRegion': {
        'parameters': {
            'region': {
                'type': 'string',
                'required': False,
                'default': 'us-east-1',
                'description': 'AWS region'
            },
            'aws_profile': {
                'type': 'string',
                'required': False,
                'default': 'default',
                'description': 'AWS profile to use'
            },
            'store_in_context': {
                'type': 'boolean',
                'required': False,
                'default': True,
                'description': 'Store results in context'
            }
        }
    },
    
    'SecurityMCPTools___GetStoredSecurityContext': {
        'parameters': {
            'region': {
                'type': 'string',
                'required': False,
                'default': 'us-east-1',
                'description': 'AWS region'
            },
            'detailed': {
                'type': 'boolean',
                'required': False,
                'default': False,
                'description': 'Return full details'
            }
        }
    }
}

# Map OpenAPI operationId to Gateway tool name
OPERATION_TO_TOOL_MAP = {
    'checkSecurityStatus': 'SecurityMCPTools___CheckSecurityServices',
    'getSecurityFindings': 'SecurityMCPTools___GetSecurityFindings',
    'checkStorageEncryption': 'SecurityMCPTools___CheckStorageEncryption',
    'checkNetworkSecurity': 'SecurityMCPTools___CheckNetworkSecurity',
    'listServicesInRegion': 'SecurityMCPTools___ListServicesInRegion',
    'getStoredContext': 'SecurityMCPTools___GetStoredSecurityContext',
}

# Map Bedrock parameter names to Gateway parameter names (per tool)
PARAMETER_NAME_MAP = {
    'SecurityMCPTools___CheckSecurityServices': {
        'region': 'region',
        'service': 'services',  # singular → plural, string → array
        'services': 'services',
        'accountId': 'account_id',  # camelCase → snake_case
        'account_id': 'account_id',
        'awsProfile': 'aws_profile',
        'aws_profile': 'aws_profile',
        'storeInContext': 'store_in_context',
        'store_in_context': 'store_in_context',
        'debug': 'debug',
    },
    
    'SecurityMCPTools___GetSecurityFindings': {
        'region': 'region',
        'service': 'service',
        'maxFindings': 'max_findings',
        'max_findings': 'max_findings',
        'severityFilter': 'severity_filter',
        'severity_filter': 'severity_filter',
        'severity': 'severity_filter',  # alias
        'awsProfile': 'aws_profile',
        'aws_profile': 'aws_profile',
        'checkEnabled': 'check_enabled',
        'check_enabled': 'check_enabled',
    },
    
    'SecurityMCPTools___CheckStorageEncryption': {
        'region': 'region',
        'service': 'services',  # singular → plural
        'services': 'services',
        'includeUnencryptedOnly': 'include_unencrypted_only',
        'include_unencrypted_only': 'include_unencrypted_only',
        'unencryptedOnly': 'include_unencrypted_only',  # alias
        'awsProfile': 'aws_profile',
        'aws_profile': 'aws_profile',
        'storeInContext': 'store_in_context',
        'store_in_context': 'store_in_context',
    },
    
    'SecurityMCPTools___CheckNetworkSecurity': {
        'region': 'region',
        'service': 'services',  # singular → plural
        'services': 'services',
        'includeNonCompliantOnly': 'include_non_compliant_only',
        'include_non_compliant_only': 'include_non_compliant_only',
        'nonCompliantOnly': 'include_non_compliant_only',  # alias
        'awsProfile': 'aws_profile',
        'aws_profile': 'aws_profile',
        'storeInContext': 'store_in_context',
        'store_in_context': 'store_in_context',
    },
    
    'SecurityMCPTools___ListServicesInRegion': {
        'region': 'region',
        'awsProfile': 'aws_profile',
        'aws_profile': 'aws_profile',
        'storeInContext': 'store_in_context',
        'store_in_context': 'store_in_context',
    },
    
    'SecurityMCPTools___GetStoredSecurityContext': {
        'region': 'region',
        'detailed': 'detailed',
    }
}


def map_parameters(operation_id, bedrock_parameters):
    """
    Map Bedrock Agent parameters to Gateway tool parameters
    
    Args:
        operation_id: OpenAPI operationId (e.g., 'checkSecurityStatus')
        bedrock_parameters: List of {name, type, value} from Bedrock event
    
    Returns:
        tuple: (tool_name, mapped_parameters)
    """
    
    # Get Gateway tool name
    tool_name = OPERATION_TO_TOOL_MAP.get(operation_id)
    if not tool_name:
        raise ValueError(f"Unknown operation: {operation_id}. Valid operations: {list(OPERATION_TO_TOOL_MAP.keys())}")
    
    # Get tool signature
    tool_sig = GATEWAY_TOOL_SIGNATURES.get(tool_name)
    if not tool_sig:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    # Get parameter name mapping for this tool
    param_map = PARAMETER_NAME_MAP.get(tool_name, {})
    
    # Start with default values
    mapped_params = {}
    for param_name, param_def in tool_sig['parameters'].items():
        default_value = param_def.get('default')
        if default_value is not None:
            mapped_params[param_name] = default_value
    
    # Map provided parameters
    for bedrock_param in bedrock_parameters:
        bedrock_name = bedrock_param.get('name')
        bedrock_value = bedrock_param.get('value')
        
        if not bedrock_name or bedrock_value is None:
            continue
        
        # Get mapped name
        gateway_name = param_map.get(bedrock_name)
        if not gateway_name:
            print(f"Warning: Unknown parameter '{bedrock_name}' for operation '{operation_id}', skipping")
            continue
        
        # Get expected type
        param_def = tool_sig['parameters'].get(gateway_name, {})
        expected_type = param_def.get('type', 'string')
        
        # Convert value to expected type
        try:
            if expected_type == 'array':
                # Convert single value to array
                if isinstance(bedrock_value, list):
                    mapped_params[gateway_name] = bedrock_value
                elif isinstance(bedrock_value, str):
                    # Split comma-separated values
                    if ',' in bedrock_value:
                        mapped_params[gateway_name] = [v.strip() for v in bedrock_value.split(',')]
                    else:
                        mapped_params[gateway_name] = [bedrock_value]
                else:
                    mapped_params[gateway_name] = [str(bedrock_value)]
            
            elif expected_type == 'integer':
                mapped_params[gateway_name] = int(bedrock_value)
            
            elif expected_type == 'boolean':
                if isinstance(bedrock_value, bool):
                    mapped_params[gateway_name] = bedrock_value
                elif isinstance(bedrock_value, str):
                    mapped_params[gateway_name] = bedrock_value.lower() in ['true', '1', 'yes', 'on']
                else:
                    mapped_params[gateway_name] = bool(bedrock_value)
            
            else:  # string
                mapped_params[gateway_name] = str(bedrock_value)
                
        except (ValueError, TypeError) as e:
            print(f"Warning: Failed to convert parameter '{bedrock_name}' to {expected_type}: {e}")
            continue
    
    # Validate required parameters
    missing_params = []
    for param_name, param_def in tool_sig['parameters'].items():
        if param_def.get('required') and (param_name not in mapped_params or mapped_params[param_name] is None):
            missing_params.append(param_name)
    
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
    
    # Remove None values (optional parameters not provided)
    mapped_params = {k: v for k, v in mapped_params.items() if v is not None}
    
    return tool_name, mapped_params


# Test cases
if __name__ == '__main__':
    print("="*80)
    print("PARAMETER MAPPING TESTS")
    print("="*80)
    
    test_cases = [
        {
            'name': 'Check security services - all params',
            'operation': 'checkSecurityStatus',
            'params': [
                {'name': 'region', 'value': 'us-east-1'},
                {'name': 'service', 'value': 'guardduty'},
                {'name': 'debug', 'value': 'true'}
            ]
        },
        {
            'name': 'Check security services - defaults',
            'operation': 'checkSecurityStatus',
            'params': []
        },
        {
            'name': 'Get findings - with severity',
            'operation': 'getSecurityFindings',
            'params': [
                {'name': 'region', 'value': 'us-west-2'},
                {'name': 'service', 'value': 'securityhub'},
                {'name': 'severity', 'value': 'HIGH'},
                {'name': 'maxFindings', 'value': '50'}
            ]
        },
        {
            'name': 'Check storage - multiple services',
            'operation': 'checkStorageEncryption',
            'params': [
                {'name': 'region', 'value': 'eu-west-1'},
                {'name': 'services', 'value': 's3,ebs,rds'},  # Comma-separated
                {'name': 'unencryptedOnly', 'value': 'true'}
            ]
        },
        {
            'name': 'Check network - non-compliant only',
            'operation': 'checkNetworkSecurity',
            'params': [
                {'name': 'region', 'value': 'ap-southeast-1'},
                {'name': 'nonCompliantOnly', 'value': 'true'}
            ]
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print("-" * 80)
        print(f"Operation: {test['operation']}")
        print(f"Bedrock Parameters: {json.dumps(test['params'], indent=2)}")
        
        try:
            tool_name, mapped_params = map_parameters(test['operation'], test['params'])
            print(f"\n✅ SUCCESS")
            print(f"Gateway Tool: {tool_name}")
            print(f"Mapped Parameters:")
            print(json.dumps(mapped_params, indent=2))
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
