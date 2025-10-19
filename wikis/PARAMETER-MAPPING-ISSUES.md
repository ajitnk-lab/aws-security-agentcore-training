# Parameter Mapping Issues - The Biggest Problem

## The Complete Flow

```
User: "Check security status for EC2 in us-east-1"
  ↓ (natural language)
Bedrock Agent: Parses intent → Decides to call action
  ↓ (structured parameters)
Action Group: {operation: "checkSecurityStatus", parameters: [{name: "region", value: "us-east-1"}, {name: "service", value: "EC2"}]}
  ↓ (Bedrock format)
Security Lambda: Must map parameters
  ↓ (MCP format)
Gateway: {name: "SecurityMCPTools___CheckSecurityServices", arguments: {region: "us-east-1", service_names: ["EC2"]}}
  ↓ (Gateway format)
Real Tool: Executes with correct parameters
```

## Issues You Faced

### Issue 1: Parameters Not Getting Passed
**Symptom:** Gateway receives empty parameters or null values
**Root Cause:** Parameter extraction from Bedrock event is wrong

**Current code problem:**
```python
parameters = event.get('parameters', [])
for param in parameters:
    param_name = param.get('name')
    param_value = param.get('value')
    # Only handles 3 specific parameters!
    if param_name == 'region':
        mcp_params['region'] = param_value
    elif param_name == 'severity':
        mcp_params['severity_filter'] = param_value
    elif param_name == 'service':
        mcp_params['services'] = [param_value]
    # What about other parameters? LOST!
```

**Problem:** Hardcoded parameter names - any other parameters are ignored.

**Solution:** Use parameter mapping table
```python
# Define all possible mappings
PARAMETER_MAP = {
    'region': 'region',
    'severity': 'severity',
    'service': 'service_names',  # Note: renamed and converted to array
    'limit': 'limit',
    'serviceType': 'service_type',
    # Add ALL parameters here
}

# Map all parameters
mcp_params = {}
for param in parameters:
    bedrock_name = param.get('name')
    bedrock_value = param.get('value')
    
    gateway_name = PARAMETER_MAP.get(bedrock_name, bedrock_name)
    mcp_params[gateway_name] = bedrock_value
```

---

### Issue 2: Default Values Not Applied
**Symptom:** Tool fails because required parameter missing
**Root Cause:** No default values when user doesn't specify parameter

**Example:**
```
User: "Check security status"
Agent: {parameters: []}  # No region specified!
Lambda: {region: ???}  # Missing required parameter
Gateway: ERROR - region is required
```

**Solution:** Apply defaults before mapping
```python
# Define defaults per tool
TOOL_DEFAULTS = {
    'SecurityMCPTools___CheckSecurityServices': {
        'region': 'us-east-1',
        'service_names': []
    }
}

# Start with defaults
tool_name = get_tool_name(operation_id)
mcp_params = TOOL_DEFAULTS.get(tool_name, {}).copy()

# Override with provided parameters
for param in parameters:
    # ... mapping logic
```

---

### Issue 3: Wrong Parameter Order/Assignment
**Symptom:** Parameters swapped or assigned to wrong tool parameter
**Root Cause:** Assuming parameter order instead of using names

**Wrong approach:**
```python
# WRONG - Assumes order
mcp_params = {
    'region': parameters[0]['value'],  # What if region is second?
    'service': parameters[1]['value']
}
```

**Correct approach:**
```python
# CORRECT - Use names
param_dict = {p['name']: p['value'] for p in parameters}
mcp_params = {
    'region': param_dict.get('region', 'us-east-1'),
    'service_names': [param_dict.get('service')] if param_dict.get('service') else []
}
```

---

### Issue 4: Wrong Parameter Names
**Symptom:** Gateway rejects request - unknown parameter
**Root Cause:** Bedrock parameter names don't match Gateway parameter names

**Examples:**
- Bedrock: `service` → Gateway: `service_names` (singular to plural)
- Bedrock: `serviceType` → Gateway: `service_type` (camelCase to snake_case)
- Bedrock: `severity` → Gateway: `severity_filter` (different name)

**Solution:** Maintain mapping table per tool
```python
PARAMETER_NAME_MAP = {
    'SecurityMCPTools___CheckSecurityServices': {
        'region': 'region',  # Same name
        'service': 'service_names',  # Different name
    },
    'SecurityMCPTools___GetSecurityFindings': {
        'region': 'region',
        'severity': 'severity',  # Same name
        'service': 'service',
    }
}
```

---

### Issue 5: Wrong Tool Mapping
**Symptom:** Gateway says tool not found
**Root Cause:** Action group operation ID doesn't match Gateway tool name

**Example:**
- OpenAPI operationId: `checkSecurityStatus`
- Gateway tool name: `SecurityMCPTools___CheckSecurityServices`
- Current code: `SecurityMCPTools___checkSecurityStatus` ❌ WRONG

**Solution:** Explicit mapping table
```python
OPERATION_TO_TOOL_MAP = {
    'checkSecurityStatus': 'SecurityMCPTools___CheckSecurityServices',
    'getSecurityFindings': 'SecurityMCPTools___GetSecurityFindings',
    'checkStorageEncryption': 'SecurityMCPTools___CheckStorageEncryption',
}

tool_name = OPERATION_TO_TOOL_MAP.get(operation_id)
if not tool_name:
    raise ValueError(f"Unknown operation: {operation_id}")
```

---

### Issue 6: Type Conversion Issues
**Symptom:** Gateway rejects parameter - wrong type
**Root Cause:** Bedrock sends all parameters as strings, Gateway expects specific types

**Examples:**
- Bedrock: `{name: "limit", value: "50"}` (string)
- Gateway expects: `{limit: 50}` (integer)

- Bedrock: `{name: "service", value: "EC2"}` (string)
- Gateway expects: `{service_names: ["EC2"]}` (array)

**Solution:** Type conversion based on tool signature
```python
TOOL_SIGNATURES = {
    'SecurityMCPTools___GetSecurityFindings': {
        'limit': {'type': 'integer'},
        'severity': {'type': 'string'},
    }
}

# Convert types
for param in parameters:
    param_name = param['name']
    param_value = param['value']
    param_type = TOOL_SIGNATURES[tool_name][param_name]['type']
    
    if param_type == 'integer':
        mcp_params[param_name] = int(param_value)
    elif param_type == 'array':
        mcp_params[param_name] = [param_value]
    else:
        mcp_params[param_name] = param_value
```

---

### Issue 7: Natural Language Parameter Extraction
**Symptom:** Agent extracts wrong parameter values from user input
**Root Cause:** Agent instruction not clear about parameter extraction

**Example:**
```
User: "Check security for my EC2 instances in Virginia"
Agent extracts: {region: "Virginia"}  ❌ Should be "us-east-1"
```

**Solution:** Improve agent instructions
```
Instructions for the Agent:
When extracting parameters:
- For region: Use AWS region codes (us-east-1, us-west-2, etc.), not names
- For service: Use AWS service names (EC2, S3, RDS, etc.)
- For severity: Use CRITICAL, HIGH, MEDIUM, LOW, or ALL
- If user says "Virginia", map to "us-east-1"
- If user says "California", map to "us-west-1"
```

---

## Complete Solution

### Step 1: Define Tool Signatures
```python
GATEWAY_TOOL_SIGNATURES = {
    'SecurityMCPTools___CheckSecurityServices': {
        'parameters': {
            'region': {'type': 'string', 'required': True, 'default': 'us-east-1'},
            'service_names': {'type': 'array', 'required': False, 'default': []},
        }
    },
    # ... all tools
}
```

### Step 2: Define Operation to Tool Mapping
```python
OPERATION_TO_TOOL_MAP = {
    'checkSecurityStatus': 'SecurityMCPTools___CheckSecurityServices',
    'getSecurityFindings': 'SecurityMCPTools___GetSecurityFindings',
    # ... all operations
}
```

### Step 3: Define Parameter Name Mapping
```python
PARAMETER_NAME_MAP = {
    'SecurityMCPTools___CheckSecurityServices': {
        'region': 'region',
        'service': 'service_names',  # Rename + convert to array
    },
    # ... all tools
}
```

### Step 4: Implement Mapper Function
```python
def map_parameters(operation_id, bedrock_parameters):
    # 1. Get tool name
    tool_name = OPERATION_TO_TOOL_MAP[operation_id]
    
    # 2. Start with defaults
    tool_sig = GATEWAY_TOOL_SIGNATURES[tool_name]
    mapped_params = {
        name: def_val['default']
        for name, def_val in tool_sig['parameters'].items()
        if def_val.get('default') is not None
    }
    
    # 3. Map provided parameters
    param_map = PARAMETER_NAME_MAP[tool_name]
    for param in bedrock_parameters:
        bedrock_name = param['name']
        bedrock_value = param['value']
        
        gateway_name = param_map.get(bedrock_name, bedrock_name)
        param_def = tool_sig['parameters'][gateway_name]
        
        # Convert type
        if param_def['type'] == 'array':
            mapped_params[gateway_name] = [bedrock_value]
        elif param_def['type'] == 'integer':
            mapped_params[gateway_name] = int(bedrock_value)
        else:
            mapped_params[gateway_name] = bedrock_value
    
    # 4. Validate required parameters
    for name, def_val in tool_sig['parameters'].items():
        if def_val.get('required') and name not in mapped_params:
            raise ValueError(f"Missing required parameter: {name}")
    
    return tool_name, mapped_params
```

---

## Testing Parameter Mapping

### Test Script
```python
# Test all operations with various parameter combinations

test_cases = [
    {
        'name': 'Check security with all params',
        'operation': 'checkSecurityStatus',
        'params': [
            {'name': 'region', 'value': 'us-east-1'},
            {'name': 'service', 'value': 'EC2'}
        ],
        'expected_tool': 'SecurityMCPTools___CheckSecurityServices',
        'expected_params': {
            'region': 'us-east-1',
            'service_names': ['EC2']
        }
    },
    {
        'name': 'Check security with defaults',
        'operation': 'checkSecurityStatus',
        'params': [],
        'expected_tool': 'SecurityMCPTools___CheckSecurityServices',
        'expected_params': {
            'region': 'us-east-1',
            'service_names': []
        }
    },
    {
        'name': 'Get findings with type conversion',
        'operation': 'getSecurityFindings',
        'params': [
            {'name': 'region', 'value': 'us-west-2'},
            {'name': 'limit', 'value': '50'}  # String to int
        ],
        'expected_tool': 'SecurityMCPTools___GetSecurityFindings',
        'expected_params': {
            'region': 'us-west-2',
            'limit': 50,  # Converted to int
            'severity': 'ALL'  # Default
        }
    }
]

for test in test_cases:
    print(f"Test: {test['name']}")
    tool_name, mapped_params = map_parameters(
        test['operation'],
        test['params']
    )
    
    assert tool_name == test['expected_tool'], f"Tool mismatch: {tool_name}"
    assert mapped_params == test['expected_params'], f"Params mismatch: {mapped_params}"
    print("  ✅ PASSED")
```

---

## Debugging Parameter Issues

### Step 1: Log Everything
```python
def lambda_handler(event, context):
    print("="*80)
    print("PARAMETER MAPPING DEBUG")
    print("="*80)
    
    operation_id = event.get('actionGroup', '')
    bedrock_params = event.get('parameters', [])
    
    print(f"1. Operation ID: {operation_id}")
    print(f"2. Bedrock Parameters:")
    for p in bedrock_params:
        print(f"   - {p['name']}: {p['value']} (type: {type(p['value'])})")
    
    try:
        tool_name, mapped_params = map_parameters(operation_id, bedrock_params)
        
        print(f"3. Gateway Tool: {tool_name}")
        print(f"4. Mapped Parameters:")
        for k, v in mapped_params.items():
            print(f"   - {k}: {v} (type: {type(v)})")
        
        print("="*80)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
```

### Step 2: Test Each Layer Separately

**Test 1: Bedrock Agent → Action Group**
```bash
# Invoke agent and check what parameters it sends
aws bedrock-agent-runtime invoke-agent \
  --agent-id AGENT_ID \
  --agent-alias-id ALIAS_ID \
  --session-id test-123 \
  --input-text "Check security status for EC2 in us-east-1" \
  response.txt

# Check Lambda logs for received parameters
aws logs filter-log-events \
  --log-group-name /aws/lambda/bedrock-gateway-proxy \
  --filter-pattern "Bedrock Parameters"
```

**Test 2: Lambda → Gateway**
```bash
# Test Lambda directly with sample event
cat > test-event.json << 'EOF'
{
  "actionGroup": "checkSecurityStatus",
  "parameters": [
    {"name": "region", "value": "us-east-1"},
    {"name": "service", "value": "EC2"}
  ]
}
EOF

aws lambda invoke \
  --function-name bedrock-gateway-proxy \
  --payload file://test-event.json \
  response.json

# Check what was sent to Gateway
cat response.json | jq .
```

**Test 3: Gateway Tool Call**
```bash
# Test Gateway directly
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "SecurityMCPTools___CheckSecurityServices",
      "arguments": {
        "region": "us-east-1",
        "service_names": ["EC2"]
      }
    }
  }'
```

---

## Checklist: Parameter Mapping

- [ ] Tool signatures defined for all Gateway tools
- [ ] Operation to tool mapping table complete
- [ ] Parameter name mapping table complete for each tool
- [ ] Default values defined for optional parameters
- [ ] Type conversion implemented (string→int, string→array)
- [ ] Required parameter validation implemented
- [ ] Logging added for debugging
- [ ] Test cases written for all operations
- [ ] Agent instructions updated with parameter format guidance
- [ ] OpenAPI schema matches parameter names

---

## Related Files

- [Parameter Mapper Implementation](../templates/parameter-mapper.py)
- [Fixed Gateway Proxy Lambda](../templates/gateway-proxy-lambda-fixed.py)
- [All Issues & Solutions](./ALL-ISSUES-AND-SOLUTIONS.md)
