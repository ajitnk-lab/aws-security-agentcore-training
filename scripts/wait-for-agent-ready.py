#!/usr/bin/env python3
"""
Wait for Bedrock Agent to be ready and stable before testing
Solves: Agent not ready, checking logs too early, lost in troubleshooting
"""
import boto3
import time
import sys
from datetime import datetime

def wait_for_agent_ready(agent_id, region='us-east-1', timeout=300):
    """
    Wait for agent to reach PREPARED state and stabilize
    Returns True if ready, False if timeout
    """
    bedrock = boto3.client('bedrock-agent', region_name=region)
    start_time = time.time()
    
    print(f"⏳ Waiting for agent {agent_id} to be ready...")
    print(f"   Timeout: {timeout}s")
    print()
    
    stable_count = 0
    required_stable_checks = 3  # Must be PREPARED for 3 consecutive checks
    
    while time.time() - start_time < timeout:
        try:
            response = bedrock.get_agent(agentId=agent_id)
            agent = response['agent']
            status = agent['agentStatus']
            updated = agent.get('updatedAt', datetime.now())
            
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed}s] Status: {status} | Stable checks: {stable_count}/{required_stable_checks}")
            
            if status == 'PREPARED':
                stable_count += 1
                if stable_count >= required_stable_checks:
                    print(f"\n✅ Agent is READY and STABLE")
                    print(f"   Status: {status}")
                    print(f"   Last updated: {updated}")
                    return True
            elif status == 'PREPARING':
                stable_count = 0
                print(f"   ⏳ Agent is preparing...")
            elif status == 'FAILED':
                print(f"\n❌ Agent preparation FAILED")
                print(f"   Check agent configuration and try again")
                return False
            else:
                stable_count = 0
                print(f"   ⚠️  Unexpected status: {status}")
            
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Error checking agent: {e}")
            return False
    
    print(f"\n⏱️  TIMEOUT after {timeout}s")
    print(f"   Agent did not reach stable PREPARED state")
    return False


def check_action_groups_ready(agent_id, region='us-east-1'):
    """Check if action groups are enabled and have Lambda targets"""
    bedrock = boto3.client('bedrock-agent', region_name=region)
    
    print("\n🔍 Checking action groups...")
    
    try:
        response = bedrock.list_agent_action_groups(
            agentId=agent_id,
            agentVersion='DRAFT',
            maxResults=100
        )
        
        action_groups = response.get('actionGroupSummaries', [])
        
        if not action_groups:
            print("   ⚠️  No action groups found")
            return False
        
        all_ready = True
        for ag in action_groups:
            ag_id = ag['actionGroupId']
            ag_name = ag['actionGroupName']
            ag_state = ag.get('actionGroupState', 'UNKNOWN')
            
            # Get details
            detail = bedrock.get_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupId=ag_id
            )
            
            ag_data = detail['agentActionGroup']
            lambda_arn = 'N/A'
            if 'actionGroupExecutor' in ag_data:
                lambda_arn = ag_data['actionGroupExecutor'].get('lambda', 'N/A')
            
            if ag_state == 'ENABLED' and lambda_arn != 'N/A':
                print(f"   ✅ {ag_name}: {ag_state}")
                print(f"      Lambda: {lambda_arn}")
            else:
                print(f"   ❌ {ag_name}: {ag_state}")
                print(f"      Lambda: {lambda_arn}")
                all_ready = False
        
        return all_ready
        
    except Exception as e:
        print(f"   ❌ Error checking action groups: {e}")
        return False


def check_lambda_permissions(agent_id, region='us-east-1'):
    """Check if Lambda has resource-based policy for agent"""
    bedrock = boto3.client('bedrock-agent', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)
    
    print("\n🔐 Checking Lambda permissions...")
    
    try:
        # Get action groups
        response = bedrock.list_agent_action_groups(
            agentId=agent_id,
            agentVersion='DRAFT',
            maxResults=100
        )
        
        for ag in response.get('actionGroupSummaries', []):
            ag_id = ag['actionGroupId']
            
            detail = bedrock.get_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupId=ag_id
            )
            
            ag_data = detail['agentActionGroup']
            if 'actionGroupExecutor' not in ag_data:
                continue
            
            lambda_arn = ag_data['actionGroupExecutor'].get('lambda')
            if not lambda_arn:
                continue
            
            # Extract function name from ARN
            function_name = lambda_arn.split(':')[-1]
            
            try:
                policy = lambda_client.get_policy(FunctionName=function_name)
                policy_doc = policy['Policy']
                
                # Check if bedrock.amazonaws.com is in policy
                if 'bedrock.amazonaws.com' in policy_doc:
                    print(f"   ✅ {function_name}: Has Bedrock permission")
                else:
                    print(f"   ❌ {function_name}: Missing Bedrock permission")
                    print(f"      Run: aws lambda add-permission --function-name {function_name} ...")
                    return False
                    
            except lambda_client.exceptions.ResourceNotFoundException:
                print(f"   ❌ {function_name}: Policy not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking Lambda permissions: {e}")
        return False


def get_recent_logs(agent_id, lambda_name=None, region='us-east-1', minutes=5):
    """Get recent CloudWatch logs"""
    logs = boto3.client('logs', region_name=region)
    
    print(f"\n📋 Recent logs (last {minutes} minutes)...")
    
    # Calculate time range
    end_time = int(time.time() * 1000)
    start_time = end_time - (minutes * 60 * 1000)
    
    # Check Lambda logs if provided
    if lambda_name:
        log_group = f"/aws/lambda/{lambda_name}"
        print(f"\n   Lambda: {lambda_name}")
        try:
            events = logs.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                limit=20
            )
            
            if events.get('events'):
                for event in events['events'][-10:]:  # Last 10 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()
                    print(f"   [{timestamp.strftime('%H:%M:%S')}] {message}")
            else:
                print(f"   ℹ️  No recent logs found")
                
        except logs.exceptions.ResourceNotFoundException:
            print(f"   ⚠️  Log group not found: {log_group}")
        except Exception as e:
            print(f"   ❌ Error fetching logs: {e}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 wait-for-agent-ready.py <agent-id> [lambda-name] [region]")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    lambda_name = sys.argv[2] if len(sys.argv) > 2 else None
    region = sys.argv[3] if len(sys.argv) > 3 else 'us-east-1'
    
    print("="*80)
    print("BEDROCK AGENT READINESS CHECK")
    print("="*80)
    
    # Step 1: Wait for agent to be ready
    if not wait_for_agent_ready(agent_id, region):
        print("\n❌ Agent is not ready. Exiting.")
        sys.exit(1)
    
    # Step 2: Check action groups
    if not check_action_groups_ready(agent_id, region):
        print("\n⚠️  Action groups have issues")
    
    # Step 3: Check Lambda permissions
    if not check_lambda_permissions(agent_id, region):
        print("\n⚠️  Lambda permissions have issues")
    
    # Step 4: Show recent logs
    if lambda_name:
        get_recent_logs(agent_id, lambda_name, region)
    
    print("\n" + "="*80)
    print("✅ READINESS CHECK COMPLETE")
    print("="*80)
    print("\nAgent is ready for testing. Wait 10-15 seconds before first invocation.")
    print("This allows AWS internal caching and routing to stabilize.")
