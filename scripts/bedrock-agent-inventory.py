#!/usr/bin/env python3
"""
Bedrock Agent Inventory - Track all agents, versions, aliases, and action groups
Solves the problem of losing track of which agent/version/action group to use
"""
import boto3
import json
from datetime import datetime

def get_agent_inventory(region='us-east-1'):
    """Get complete inventory of all Bedrock agents and their components"""
    bedrock = boto3.client('bedrock-agent', region_name=region)
    
    inventory = {
        'timestamp': datetime.now().isoformat(),
        'region': region,
        'agents': []
    }
    
    # List all agents
    agents_response = bedrock.list_agents(maxResults=100)
    
    for agent_summary in agents_response.get('agentSummaries', []):
        agent_id = agent_summary['agentId']
        
        # Get full agent details
        agent_detail = bedrock.get_agent(agentId=agent_id)
        agent = agent_detail['agent']
        
        agent_info = {
            'id': agent_id,
            'name': agent['agentName'],
            'status': agent['agentStatus'],
            'created': agent.get('createdAt', '').isoformat() if agent.get('createdAt') else 'N/A',
            'updated': agent.get('updatedAt', '').isoformat() if agent.get('updatedAt') else 'N/A',
            'model': agent.get('foundationModel', 'N/A'),
            'versions': [],
            'aliases': [],
            'action_groups': []
        }
        
        # List versions
        try:
            versions = bedrock.list_agent_versions(agentId=agent_id, maxResults=100)
            for v in versions.get('agentVersionSummaries', []):
                agent_info['versions'].append({
                    'version': v['agentVersion'],
                    'status': v['agentStatus'],
                    'created': v.get('createdAt', '').isoformat() if v.get('createdAt') else 'N/A'
                })
        except Exception as e:
            print(f"Warning: Could not list versions for {agent_id}: {e}")
        
        # List aliases
        try:
            aliases = bedrock.list_agent_aliases(agentId=agent_id, maxResults=100)
            for a in aliases.get('agentAliasSummaries', []):
                agent_info['aliases'].append({
                    'id': a['agentAliasId'],
                    'name': a['agentAliasName'],
                    'status': a.get('agentAliasStatus', 'N/A'),
                    'routing': a.get('routingConfiguration', [])
                })
        except Exception as e:
            print(f"Warning: Could not list aliases for {agent_id}: {e}")
        
        # List action groups for DRAFT version
        try:
            action_groups = bedrock.list_agent_action_groups(
                agentId=agent_id,
                agentVersion='DRAFT',
                maxResults=100
            )
            for ag in action_groups.get('actionGroupSummaries', []):
                ag_detail = bedrock.get_agent_action_group(
                    agentId=agent_id,
                    agentVersion='DRAFT',
                    actionGroupId=ag['actionGroupId']
                )
                ag_data = ag_detail['agentActionGroup']
                
                lambda_arn = 'N/A'
                if 'actionGroupExecutor' in ag_data:
                    lambda_arn = ag_data['actionGroupExecutor'].get('lambda', 'N/A')
                
                agent_info['action_groups'].append({
                    'id': ag['actionGroupId'],
                    'name': ag['actionGroupName'],
                    'state': ag.get('actionGroupState', 'N/A'),
                    'updated': ag.get('updatedAt', '').isoformat() if ag.get('updatedAt') else 'N/A',
                    'lambda': lambda_arn
                })
        except Exception as e:
            print(f"Warning: Could not list action groups for {agent_id}: {e}")
        
        inventory['agents'].append(agent_info)
    
    return inventory


def print_inventory(inventory):
    """Print inventory in readable format"""
    print(f"\n{'='*80}")
    print(f"BEDROCK AGENT INVENTORY - {inventory['timestamp']}")
    print(f"Region: {inventory['region']}")
    print(f"{'='*80}\n")
    
    if not inventory['agents']:
        print("No agents found.")
        return
    
    for agent in inventory['agents']:
        print(f"🤖 AGENT: {agent['name']}")
        print(f"   ID: {agent['id']}")
        print(f"   Status: {agent['status']}")
        print(f"   Model: {agent['model']}")
        print(f"   Created: {agent['created']}")
        print(f"   Updated: {agent['updated']}")
        
        if agent['versions']:
            print(f"\n   📦 VERSIONS ({len(agent['versions'])}):")
            for v in agent['versions']:
                print(f"      • {v['version']} - {v['status']} (created: {v['created']})")
        
        if agent['aliases']:
            print(f"\n   🏷️  ALIASES ({len(agent['aliases'])}):")
            for a in agent['aliases']:
                routing = a['routing']
                version = routing[0]['agentVersion'] if routing else 'N/A'
                print(f"      • {a['name']} (ID: {a['id']}) → Version {version} - {a['status']}")
        
        if agent['action_groups']:
            print(f"\n   ⚡ ACTION GROUPS ({len(agent['action_groups'])}):")
            for ag in agent['action_groups']:
                print(f"      • {ag['name']} (ID: {ag['id']}) - {ag['state']}")
                print(f"        Lambda: {ag['lambda']}")
                print(f"        Updated: {ag['updated']}")
        
        print(f"\n{'-'*80}\n")


def save_inventory(inventory, filename='agent-inventory.json'):
    """Save inventory to JSON file"""
    with open(filename, 'w') as f:
        json.dump(inventory, f, indent=2, default=str)
    print(f"✅ Inventory saved to {filename}")


def find_agent_by_name(inventory, name):
    """Find agent by name (case-insensitive partial match)"""
    matches = []
    name_lower = name.lower()
    for agent in inventory['agents']:
        if name_lower in agent['name'].lower():
            matches.append(agent)
    return matches


def get_active_config(agent_info):
    """Get the active configuration to use for invocation"""
    config = {
        'agent_id': agent_info['id'],
        'agent_name': agent_info['name'],
        'recommended_alias': None,
        'action_groups': []
    }
    
    # Find active alias (prefer non-DRAFT)
    for alias in agent_info['aliases']:
        if alias['status'] == 'PREPARED':
            config['recommended_alias'] = alias['name']
            break
    
    # List enabled action groups
    for ag in agent_info['action_groups']:
        if ag['state'] == 'ENABLED':
            config['action_groups'].append({
                'name': ag['name'],
                'id': ag['id'],
                'lambda': ag['lambda']
            })
    
    return config


if __name__ == '__main__':
    import sys
    
    region = sys.argv[1] if len(sys.argv) > 1 else 'us-east-1'
    
    print("Fetching Bedrock Agent inventory...")
    inventory = get_agent_inventory(region)
    
    # Print to console
    print_inventory(inventory)
    
    # Save to file
    save_inventory(inventory)
    
    # Show quick reference
    print("\n" + "="*80)
    print("QUICK REFERENCE - Active Configurations")
    print("="*80 + "\n")
    
    for agent in inventory['agents']:
        if agent['status'] == 'PREPARED':
            config = get_active_config(agent)
            print(f"Agent: {config['agent_name']}")
            print(f"  ID: {config['agent_id']}")
            print(f"  Alias: {config['recommended_alias'] or 'Use DRAFT'}")
            print(f"  Action Groups: {len(config['action_groups'])}")
            for ag in config['action_groups']:
                print(f"    - {ag['name']}")
            print()
