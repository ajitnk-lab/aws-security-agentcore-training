#!/usr/bin/env python3
import json
import sys

def validate_bedrock_schema(schema_file):
    """Validate OpenAPI schema for Bedrock Agent requirements"""
    
    with open(schema_file, 'r') as f:
        schema = json.load(f)
    
    errors = []
    
    # Check OpenAPI version
    if schema.get('openapi') != '3.0.0':
        errors.append(f"❌ OpenAPI version must be 3.0.0, found: {schema.get('openapi')}")
    
    # Check required top-level fields
    if 'info' not in schema:
        errors.append("❌ Missing required 'info' field")
    elif 'title' not in schema['info'] or 'version' not in schema['info']:
        errors.append("❌ 'info' must contain 'title' and 'version'")
    
    if 'paths' not in schema or not schema['paths']:
        errors.append("❌ Missing or empty 'paths' field")
    
    # Check each path
    for path, methods in schema.get('paths', {}).items():
        for method, details in methods.items():
            if 'operationId' not in details:
                errors.append(f"❌ Missing 'operationId' in {method.upper()} {path}")
            if 'description' not in details:
                errors.append(f"⚠️  Missing 'description' in {method.upper()} {path}")
            if 'responses' not in details:
                errors.append(f"❌ Missing 'responses' in {method.upper()} {path}")
    
    if errors:
        print("Schema validation failed:\n")
        for error in errors:
            print(error)
        return False
    
    print("✅ Schema is valid for Bedrock Agent")
    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 validate-openapi-schema.py <schema.json>")
        sys.exit(1)
    
    valid = validate_bedrock_schema(sys.argv[1])
    sys.exit(0 if valid else 1)
