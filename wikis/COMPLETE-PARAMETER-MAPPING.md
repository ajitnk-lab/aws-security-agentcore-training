# Complete Parameter Mapping - All 12+ Parameters

## All Parameters Across All Tools

### Common Parameters (appear in multiple tools):
1. **region** - AWS region (default: us-east-1)
2. **aws_profile** - AWS profile to use (default: default)
3. **store_in_context** - Store results in context (default: true)
4. **debug** - Include debug info (default: true)

### Tool-Specific Parameters:

#### CheckSecurityServices (6 parameters)
1. region
2. **services** - Array of security services (guardduty, inspector, accessanalyzer, securityhub, trustedadvisor, macie)
3. **account_id** - Optional AWS account ID
4. aws_profile
5. store_in_context
6. debug

#### GetSecurityFindings (6 parameters)
1. region
2. **service** - Single security service (required)
3. **max_findings** - Max number of findings (default: 100)
4. **severity_filter** - Severity filter (HIGH, CRITICAL, etc.)
5. aws_profile
6. **check_enabled** - Check if service enabled first (default: true)

#### CheckStorageEncryption (5 parameters)
1. region
2. **services** - Array of storage services (s3, ebs, rds, dynamodb, efs, elasticache)
3. **include_unencrypted_only** - Show only unencrypted (default: false)
4. aws_profile
5. store_in_context

#### CheckNetworkSecurity (5 parameters)
1. region
2. **services** - Array of network services (elb, vpc, apigateway, cloudfront)
3. **include_non_compliant_only** - Show only non-compliant (default: false)
4. aws_profile
5. store_in_context

#### ListServicesInRegion (3 parameters)
1. region
2. aws_profile
3. store_in_context

#### GetStoredSecurityContext (2 parameters)
1. region
2. **detailed** - Return full details (default: false)

## Critical Mappings

### Parameter Name Transformations

| Bedrock Name | Gateway Name | Transformation |
|--------------|--------------|----------------|
| service | services | Singular → Plural + String → Array |
| services | services | Direct (already array) |
| accountId | account_id | camelCase → snake_case |
| awsProfile | aws_profile | camelCase → snake_case |
| storeInContext | store_in_context | camelCase → snake_case |
| maxFindings | max_findings | camelCase → snake_case |
| severityFilter | severity_filter | camelCase → snake_case |
| severity | severity_filter | Alias mapping |
| includeUnencryptedOnly | include_unencrypted_only | camelCase → snake_case |
| unencryptedOnly | include_unencrypted_only | Alias + camelCase → snake_case |
| includeNonCompliantOnly | include_non_compliant_only | camelCase → snake_case |
| nonCompliantOnly | include_non_compliant_only | Alias + camelCase → snake_case |
| checkEnabled | check_enabled | camelCase → snake_case |

### Type Conversions

| Bedrock Type | Gateway Type | Conversion |
|--------------|--------------|------------|
| "50" (string) | 50 (integer) | int(value) |
| "true" (string) | true (boolean) | value.lower() in ['true', '1', 'yes'] |
| "EC2" (string) | ["EC2"] (array) | [value] |
| "s3,ebs,rds" (string) | ["s3", "ebs", "rds"] (array) | value.split(',') |

## Operation to Tool Mapping

| OpenAPI operationId | Gateway Tool Name |
|---------------------|-------------------|
| checkSecurityStatus | SecurityMCPTools___CheckSecurityServices |
| getSecurityFindings | SecurityMCPTools___GetSecurityFindings |
| checkStorageEncryption | SecurityMCPTools___CheckStorageEncryption |
| checkNetworkSecurity | SecurityMCPTools___CheckNetworkSecurity |
| listServicesInRegion | SecurityMCPTools___ListServicesInRegion |
| getStoredContext | SecurityMCPTools___GetStoredSecurityContext |

## Example Mappings

### Example 1: User says "Check security for EC2"
```
User Input: "Check security status for EC2 in us-east-1"
  ↓
Agent Extracts:
{
  "operation": "checkSecurityStatus",
  "parameters": [
    {"name": "region", "value": "us-east-1"},
    {"name": "service", "value": "EC2"}
  ]
}
  ↓
Lambda Maps:
{
  "tool": "SecurityMCPTools___CheckSecurityServices",
  "arguments": {
    "region": "us-east-1",
    "services": ["guardduty"],  // EC2 → guardduty service
    "aws_profile": "default",
    "store_in_context": true,
    "debug": true
  }
}
```

### Example 2: User says "Get high severity findings"
```
User Input: "Get high severity security findings from SecurityHub"
  ↓
Agent Extracts:
{
  "operation": "getSecurityFindings",
  "parameters": [
    {"name": "service", "value": "securityhub"},
    {"name": "severity", "value": "HIGH"}
  ]
}
  ↓
Lambda Maps:
{
  "tool": "SecurityMCPTools___GetSecurityFindings",
  "arguments": {
    "region": "us-east-1",  // Default
    "service": "securityhub",
    "severity_filter": "HIGH",  // severity → severity_filter
    "max_findings": 100,  // Default
    "aws_profile": "default",
    "check_enabled": true
  }
}
```

### Example 3: User says "Check unencrypted S3 buckets"
```
User Input: "Check for unencrypted S3 buckets in eu-west-1"
  ↓
Agent Extracts:
{
  "operation": "checkStorageEncryption",
  "parameters": [
    {"name": "region", "value": "eu-west-1"},
    {"name": "services", "value": "s3"},
    {"name": "unencryptedOnly", "value": "true"}
  ]
}
  ↓
Lambda Maps:
{
  "tool": "SecurityMCPTools___CheckStorageEncryption",
  "arguments": {
    "region": "eu-west-1",
    "services": ["s3"],  // String → Array
    "include_unencrypted_only": true,  // unencryptedOnly → include_unencrypted_only
    "aws_profile": "default",
    "store_in_context": true
  }
}
```

## Agent Instructions for Parameter Extraction

Add this to your Bedrock Agent instructions:

```
When extracting parameters from user requests:

1. Region:
   - Use AWS region codes (us-east-1, us-west-2, eu-west-1, etc.)
   - Map common names: "Virginia" → "us-east-1", "California" → "us-west-1", "Ireland" → "eu-west-1"
   - Default to "us-east-1" if not specified

2. Services:
   - For security services: guardduty, inspector, accessanalyzer, securityhub, trustedadvisor, macie
   - For storage services: s3, ebs, rds, dynamodb, efs, elasticache
   - For network services: elb, vpc, apigateway, cloudfront
   - Use lowercase service names

3. Severity:
   - Use: CRITICAL, HIGH, MEDIUM, LOW
   - For Trusted Advisor: ERROR, WARNING

4. Boolean flags:
   - Use "true" or "false" as strings
   - Examples: unencryptedOnly="true", nonCompliantOnly="true"

5. Numbers:
   - Pass as strings, Lambda will convert
   - Example: maxFindings="50"
```

## Implementation

Use the complete parameter mapper:
```python
from templates.complete_parameter_mapper import map_parameters

def lambda_handler(event, context):
    operation_id = event.get('actionGroup', '')
    bedrock_parameters = event.get('parameters', [])
    
    # Map parameters
    tool_name, mapped_params = map_parameters(operation_id, bedrock_parameters)
    
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
```

## Testing

Run the test suite:
```bash
cd /persistent/home/ubuntu/workspace/training
python3 templates/complete-parameter-mapper.py
```

All 5 test cases should pass with ✅ SUCCESS.

## Related Files

- [Complete Parameter Mapper](../templates/complete-parameter-mapper.py) - Working implementation
- [Parameter Mapping Issues](./PARAMETER-MAPPING-ISSUES.md) - Common problems
- [Fixed Gateway Proxy Lambda](../templates/gateway-proxy-lambda-fixed.py) - Integration example
