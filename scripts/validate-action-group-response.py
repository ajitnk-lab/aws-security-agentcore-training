#!/usr/bin/env python3
"""
Validates Bedrock Agent Action Group Lambda response format
Run this against your Lambda to catch format errors BEFORE deployment
"""
import json
import sys

def validate_response(response):
    """Validate response matches Bedrock Agent requirements"""
    errors = []
    
    # Check top-level structure
    if not isinstance(response, dict):
        errors.append("❌ Response must be a dictionary")
        return errors
    
    # Required: messageVersion
    if 'messageVersion' not in response:
        errors.append("❌ Missing required field: 'messageVersion'")
    elif response['messageVersion'] != '1.0':
        errors.append(f"❌ messageVersion must be '1.0', got: {response['messageVersion']}")
    
    # Required: response object
    if 'response' not in response:
        errors.append("❌ Missing required field: 'response'")
        return errors
    
    resp = response['response']
    
    # Required fields in response
    required = ['actionGroup', 'apiPath', 'httpMethod', 'httpStatusCode', 'responseBody']
    for field in required:
        if field not in resp:
            errors.append(f"❌ Missing required field in response: '{field}'")
    
    # Validate httpStatusCode
    if 'httpStatusCode' in resp:
        if not isinstance(resp['httpStatusCode'], int):
            errors.append(f"❌ httpStatusCode must be integer, got: {type(resp['httpStatusCode'])}")
        elif resp['httpStatusCode'] not in [200, 400, 404, 500]:
            errors.append(f"⚠️  Unusual httpStatusCode: {resp['httpStatusCode']}")
    
    # Validate responseBody structure
    if 'responseBody' in resp:
        if not isinstance(resp['responseBody'], dict):
            errors.append("❌ responseBody must be a dictionary")
        elif 'application/json' not in resp['responseBody']:
            errors.append("❌ responseBody must contain 'application/json' key")
        else:
            json_body = resp['responseBody']['application/json']
            if 'body' not in json_body:
                errors.append("❌ responseBody['application/json'] must contain 'body' key")
            else:
                body = json_body['body']
                # Body must be a JSON STRING, not dict
                if not isinstance(body, str):
                    errors.append(f"❌ CRITICAL: body must be JSON STRING, got {type(body).__name__}")
                    errors.append("   Fix: Use json.dumps() on your data before returning")
                else:
                    # Try to parse to ensure valid JSON
                    try:
                        json.loads(body)
                    except json.JSONDecodeError as e:
                        errors.append(f"❌ body is not valid JSON: {e}")
    
    return errors


def test_lambda_response(test_file):
    """Test a Lambda response from file"""
    with open(test_file, 'r') as f:
        response = json.load(f)
    
    errors = validate_response(response)
    
    if errors:
        print("❌ Response validation FAILED:\n")
        for error in errors:
            print(error)
        return False
    
    print("✅ Response format is VALID for Bedrock Agent")
    return True


# Example test responses
VALID_EXAMPLE = {
    "messageVersion": "1.0",
    "response": {
        "actionGroup": "SecurityActions",
        "apiPath": "/check-security-status",
        "httpMethod": "POST",
        "httpStatusCode": 200,
        "responseBody": {
            "application/json": {
                "body": json.dumps({"status": "success", "findings": []})
            }
        }
    }
}

INVALID_EXAMPLES = [
    {
        "name": "Missing messageVersion",
        "response": {
            "response": {
                "actionGroup": "test",
                "apiPath": "/test",
                "httpMethod": "POST",
                "httpStatusCode": 200,
                "responseBody": {"application/json": {"body": "{}"}}
            }
        }
    },
    {
        "name": "Body is dict not string",
        "response": {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "test",
                "apiPath": "/test",
                "httpMethod": "POST",
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": {"status": "success"}  # WRONG: dict not string
                    }
                }
            }
        }
    },
    {
        "name": "Missing responseBody",
        "response": {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": "test",
                "apiPath": "/test",
                "httpMethod": "POST",
                "httpStatusCode": 200
            }
        }
    }
]


if __name__ == '__main__':
    if len(sys.argv) == 2:
        # Validate from file
        valid = test_lambda_response(sys.argv[1])
        sys.exit(0 if valid else 1)
    else:
        # Run examples
        print("Testing VALID example:")
        validate_response(VALID_EXAMPLE)
        print("\n" + "="*60 + "\n")
        
        for example in INVALID_EXAMPLES:
            print(f"Testing INVALID example: {example['name']}")
            validate_response(example['response'])
            print("\n" + "="*60 + "\n")
