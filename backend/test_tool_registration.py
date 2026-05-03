#!/usr/bin/env python3
"""
Test script to verify tool registration.

This script imports the tool registry and verifies that all 53 tools
are properly registered with their comprehensive metadata.

Note: Query service tools (7) are excluded as they're not for agent use.
"""

import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.tools import initialize_tools
from app.models.agent import AgentType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Test tool registration."""
    logger.info("=" * 80)
    logger.info("TOOL REGISTRATION TEST")
    logger.info("=" * 80)
    
    # Initialize tools
    logger.info("\n1. Initializing tool registry...")
    try:
        registry = initialize_tools()
        logger.info("✓ Tool registry initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize tool registry: {e}")
        return 1
    
    # Get all tools
    logger.info("\n2. Checking registered tools...")
    all_tools = registry.get_all_tools()
    logger.info(f"✓ Total tools registered: {len(all_tools)}")
    
    # Expected tool count (53 agent tools, query tools excluded)
    expected_count = 53
    if len(all_tools) == expected_count:
        logger.info(f"✓ Tool count matches expected: {expected_count}")
    else:
        logger.warning(f"⚠ Tool count mismatch: expected {expected_count}, got {len(all_tools)}")
    
    # Check tools by domain
    logger.info("\n3. Checking tools by agent domain...")
    domains = [
        ("discovery", "Discovery"),
        ("metrics", "Metrics"),
        ("security", "Security"),
        ("compliance", "Compliance"),
        ("optimization", "Optimization"),
        ("prediction", "Prediction"),
    ]
    
    for domain, name in domains:
        tools = registry.get_tools_by_domain(domain)
        logger.info(f"  {name:15} : {len(tools):2} tools")
    
    # Sample tool details
    logger.info("\n4. Sample tool details...")
    sample_tools = [
        "create_gateway",
        "list_all_apis",
        "get_security_summary",
        "list_optimization_recommendations",
        "get_prediction"
    ]
    
    for tool_name in sample_tools:
        tool = registry.get_tool(tool_name)
        if tool:
            desc_preview = tool.description[:100].replace('\n', ' ') + "..."
            logger.info(f"  ✓ {tool_name}: {desc_preview}")
        else:
            logger.warning(f"  ✗ {tool_name}: NOT FOUND")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total tools registered: {len(all_tools)}")
    logger.info(f"Expected tools: {expected_count}")
    logger.info(f"Status: {'✓ PASS' if len(all_tools) == expected_count else '⚠ PARTIAL'}")
    logger.info("=" * 80)
    
    return 0 if len(all_tools) == expected_count else 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
