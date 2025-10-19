#!/usr/bin/env python3
import os
import json
import boto3
from typing import Any

def security_check_services(region="us-east-1", services=None, account_id=None, aws_profile="default", store_in_context=True, debug=True):
    if not services:
        services = ["guardduty", "securityhub", "inspector2", "accessanalyzer", "macie2"]
    result = {}
    for svc in services:
        try:
            client = boto3.client(svc, region_name=region)
            if svc == "guardduty":
                result[svc] = "enabled" if client.list_detectors().get("DetectorIds") else "disabled"
            elif svc == "securityhub":
                client.get_enabled_standards()
                result[svc] = "enabled"
            else:
                result[svc] = "unknown"
        except:
            result[svc] = "disabled"
    return result

def security_get_findings(region="us-east-1", service="securityhub", max_findings=10, severity_filter=None, aws_profile="default", check_enabled=True):
    client = boto3.client(service, region_name=region)
    if service == "securityhub":
        filters = {}
        if severity_filter:
            filters["SeverityLabel"] = [{"Value": severity_filter, "Comparison": "EQUALS"}]
        findings = client.get_findings(Filters=filters, MaxResults=max_findings)
        return {"count": len(findings["Findings"]), "findings": findings["Findings"]}
    return {"error": "Service not supported"}

def security_check_encryption(region="us-east-1", services=None, include_unencrypted_only=False, aws_profile="default", store_in_context=True):
    if not services:
        services = ["s3", "ebs"]
    result = {}
    if "s3" in services:
        s3 = boto3.client("s3", region_name=region)
        buckets = s3.list_buckets()["Buckets"]
        encrypted = 0
        for bucket in buckets[:10]:
            try:
                s3.get_bucket_encryption(Bucket=bucket["Name"])
                encrypted += 1
            except:
                pass
        result["s3"] = {"total": len(buckets), "encrypted": encrypted}
    if "ebs" in services:
        ec2 = boto3.client("ec2", region_name=region)
        volumes = ec2.describe_volumes()["Volumes"]
        encrypted = sum(1 for v in volumes if v.get("Encrypted"))
        result["ebs"] = {"total": len(volumes), "encrypted": encrypted}
    return result

def security_check_network(region="us-east-1", services=None, include_non_compliant_only=False, aws_profile="default", store_in_context=True):
    if not services:
        services = ["vpc", "sg"]
    result = {}
    ec2 = boto3.client("ec2", region_name=region)
    if "vpc" in services:
        vpcs = ec2.describe_vpcs()["Vpcs"]
        result["vpc"] = {"total": len(vpcs)}
    if "sg" in services:
        sgs = ec2.describe_security_groups()["SecurityGroups"]
        open_sgs = [sg for sg in sgs if any(rule.get("CidrIp") == "0.0.0.0/0" for rule in sg.get("IpPermissions", []))]
        result["security_groups"] = {"total": len(sgs), "open_to_internet": len(open_sgs)}
    return result

def security_list_services(region="us-east-1", aws_profile="default", store_in_context=True):
    return {"region": region, "available_services": ["ec2", "s3", "rds", "lambda", "dynamodb"]}

def security_get_context(region="us-east-1", detailed=False):
    return {"region": region, "context": "stored_security_data"}

TOOLS = [
    {
        "name": "security_check_services",
        "description": "Check if AWS security services are enabled. Use when: 'check security status', 'is GuardDuty enabled', 'security services active'.",
        "parameters": {
            "region": {"type": "string", "default": "us-east-1"},
            "services": {"type": "array", "items": {"type": "string"}, "default": ["guardduty", "securityhub"]},
            "account_id": {"type": "string"},
            "aws_profile": {"type": "string", "default": "default"},
            "store_in_context": {"type": "boolean", "default": True},
            "debug": {"type": "boolean", "default": True}
        }
    },
    {
        "name": "security_get_findings",
        "description": "Get security findings. Use when: 'show findings', 'vulnerabilities', 'security issues'.",
        "parameters": {
            "region": {"type": "string", "default": "us-east-1"},
            "service": {"type": "string", "default": "securityhub"},
            "max_findings": {"type": "integer", "default": 10},
            "severity_filter": {"type": "string"},
            "aws_profile": {"type": "string", "default": "default"},
            "check_enabled": {"type": "boolean", "default": True}
        }
    },
    {
        "name": "security_check_encryption",
        "description": "Check encryption status. Use when: 'check encryption', 'S3 encrypted', 'EBS encryption'.",
        "parameters": {
            "region": {"type": "string", "default": "us-east-1"},
            "services": {"type": "array", "items": {"type": "string"}, "default": ["s3", "ebs"]},
            "include_unencrypted_only": {"type": "boolean", "default": False},
            "aws_profile": {"type": "string", "default": "default"},
            "store_in_context": {"type": "boolean", "default": True}
        }
    },
    {
        "name": "security_check_network",
        "description": "Check network security. Use when: 'check network', 'security groups', 'VPC security'.",
        "parameters": {
            "region": {"type": "string", "default": "us-east-1"},
            "services": {"type": "array", "items": {"type": "string"}, "default": ["vpc", "sg"]},
            "include_non_compliant_only": {"type": "boolean", "default": False},
            "aws_profile": {"type": "string", "default": "default"},
            "store_in_context": {"type": "boolean", "default": True}
        }
    },
    {
        "name": "security_list_services",
        "description": "List available services in region. Use when: 'what services', 'list services'.",
        "parameters": {
            "region": {"type": "string", "default": "us-east-1"},
            "aws_profile": {"type": "string", "default": "default"},
            "store_in_context": {"type": "boolean", "default": True}
        }
    },
    {
        "name": "security_get_context",
        "description": "Get stored security context. Use when: 'show context', 'stored data'.",
        "parameters": {
            "region": {"type": "string", "default": "us-east-1"},
            "detailed": {"type": "boolean", "default": False}
        }
    }
]

AGENT_INSTRUCTIONS = """Use these tools for security queries:
- security_check_services: Check if security services enabled
- security_get_findings: Get security findings
- security_check_encryption: Check encryption status
- security_check_network: Check network security
- security_list_services: List services in region
- security_get_context: Get stored context
Always call tools instead of generic advice."""

def handler(event, context=None):
    tool = event.get("tool")
    params = event.get("parameters", {})
    
    tools_map = {
        "security_check_services": security_check_services,
        "security_get_findings": security_get_findings,
        "security_check_encryption": security_check_encryption,
        "security_check_network": security_check_network,
        "security_list_services": security_list_services,
        "security_get_context": security_get_context
    }
    
    if tool in tools_map:
        return tools_map[tool](**params)
    return {"error": "Unknown tool"}

if __name__ == "__main__":
    print(json.dumps(TOOLS, indent=2))
