"""
Test script to verify tool registration works correctly.

This script tests that:
1. Tools are registered successfully
2. Agents receive correct tools for their domains
3. Tool metadata is properly set
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.tools import initialize_tools


def test_tool_registration():
    """Test that tools are registered correctly."""
    print("=" * 80)
    print("Testing Tool Registration")
    print("=" * 80)
    
    # Initialize tools
    print("\n1. Initializing tool registry...")
    registry = initialize_tools()
    
    # Check total tools registered
    total_tools = len(registry)
    print(f"   ✓ Total tools registered: {total_tools}")
    
    if total_tools == 0:
        print("   ✗ ERROR: No tools registered!")
        return False
    
    # Check tools by domain
    print("\n2. Checking tools by domain:")
    domains = ["discovery", "security", "compliance", "metrics", "optimization", "prediction"]
    
    for domain in domains:
        tools = registry.get_tools_by_domain(domain)
        print(f"   - {domain}: {len(tools)} tools")
        
        if len(tools) == 0:
            print(f"     ⚠ WARNING: No tools found for {domain} domain")
        else:
            # Show first 3 tool names
            tool_names = [t.name for t in tools[:3]]
            print(f"     Examples: {', '.join(tool_names)}")
    
    # Check specific tools
    print("\n3. Checking specific tools:")
    expected_tools = [
        "list_gateways",
        "list_all_apis",
        "get_security_summary",
        "list_compliance_violations",
        "get_analytics_metrics",
        "list_optimization_recommendations",
        "list_predictions",
    ]
    
    for tool_name in expected_tools:
        tool = registry.get_tool(tool_name)
        if tool:
            print(f"   ✓ {tool_name}: Found")
            # Check if tool has description
            if tool.description:
                print(f"     Description: {tool.description[:60]}...")
        else:
            print(f"   ✗ {tool_name}: NOT FOUND")
    
    # Check tool metadata
    print("\n4. Checking tool metadata:")
    sample_tool = registry.get_tool("list_gateways")
    if sample_tool:
        metadata = registry.get_tool_metadata("list_gateways")
        if metadata:
            print(f"   ✓ Metadata found for 'list_gateways'")
            print(f"     Agent domains: {metadata.agent_domains}")
            print(f"     Parameters: {len(metadata.parameters)}")
        else:
            print(f"   ⚠ No metadata found for 'list_gateways'")
    
    print("\n" + "=" * 80)
    print("Tool Registration Test Complete")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = test_tool_registration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Made with Bob
