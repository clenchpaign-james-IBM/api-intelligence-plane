#!/usr/bin/env python3
"""
Migration script to extend queries index with agentic query fields.

This script adds new fields to the existing queries index to support
the agentic query service (Feature: 001-agentic-query).

New fields:
- execution_mode: Execution mode (agentic or fallback)
- agent_decisions: List of agent decisions made
- tool_invocations: List of tool invocations
- fallback_reason: Reason for fallback (if mode=fallback)

Usage:
    python backend/scripts/extend_queries_index.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from opensearchpy import OpenSearch

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Index name
QUERIES_INDEX = "queries"

# New field mappings for agentic query support
AGENTIC_FIELD_MAPPINGS = {
    "properties": {
        "execution_mode": {
            "type": "keyword",
            "ignore_above": 256
        },
        "agent_decisions": {
            "type": "nested",
            "properties": {
                "decision_id": {"type": "keyword"},
                "agent_type": {"type": "keyword"},
                "query_text": {"type": "text"},
                "reasoning": {"type": "text"},
                "selected_tools": {"type": "keyword"},
                "tool_parameters": {"type": "object", "enabled": False},
                "confidence_score": {"type": "float"},
                "timestamp": {"type": "date"},
                "execution_time_ms": {"type": "integer"},
                "context_used": {"type": "object", "enabled": False}
            }
        },
        "tool_invocations": {
            "type": "nested",
            "properties": {
                "invocation_id": {"type": "keyword"},
                "tool_name": {"type": "keyword"},
                "agent_type": {"type": "keyword"},
                "parameters": {"type": "object", "enabled": False},
                "result": {"type": "object", "enabled": False},
                "success": {"type": "boolean"},
                "error": {"type": "text"},
                "execution_time_ms": {"type": "integer"},
                "timestamp": {"type": "date"},
                "retry_count": {"type": "integer"}
            }
        },
        "fallback_reason": {
            "type": "keyword",
            "ignore_above": 256
        }
    }
}


async def check_index_exists(client: OpenSearch, index_name: str) -> bool:
    """Check if an index exists."""
    try:
        return client.indices.exists(index=index_name)
    except Exception as e:
        logger.error(f"Error checking index existence: {e}")
        return False


async def get_current_mapping(client: OpenSearch, index_name: str) -> dict:
    """Get current index mapping."""
    try:
        response = client.indices.get_mapping(index=index_name)
        return response[index_name]["mappings"]
    except Exception as e:
        logger.error(f"Error getting current mapping: {e}")
        return {}


async def extend_index_mapping(client: OpenSearch, index_name: str) -> bool:
    """
    Extend the queries index with agentic query fields.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Extending {index_name} index with agentic query fields...")
        
        # Check if index exists
        if not await check_index_exists(client, index_name):
            logger.error(f"Index {index_name} does not exist. Please create it first.")
            return False
        
        # Get current mapping
        current_mapping = await get_current_mapping(client, index_name)
        logger.info(f"Current mapping retrieved for {index_name}")
        
        # Check if fields already exist
        existing_properties = current_mapping.get("properties", {})
        if "execution_mode" in existing_properties:
            logger.warning("Agentic query fields already exist in the index")
            logger.info("Verifying field mappings...")
            
            # Still update to ensure mappings are correct
            client.indices.put_mapping(
                index=index_name,
                body=AGENTIC_FIELD_MAPPINGS
            )
            logger.info("Field mappings verified and updated")
            return True
        
        # Add new fields to the index
        logger.info("Adding new agentic query fields...")
        client.indices.put_mapping(
            index=index_name,
            body=AGENTIC_FIELD_MAPPINGS
        )
        
        logger.info(f"Successfully extended {index_name} index with agentic query fields")
        logger.info("New fields added:")
        logger.info("  - execution_mode (keyword)")
        logger.info("  - agent_decisions (nested)")
        logger.info("  - tool_invocations (nested)")
        logger.info("  - fallback_reason (keyword)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error extending index mapping: {e}", exc_info=True)
        return False


async def verify_migration(client: OpenSearch, index_name: str) -> bool:
    """
    Verify that the migration was successful.
    
    Returns:
        True if all fields exist, False otherwise
    """
    try:
        logger.info("Verifying migration...")
        
        mapping = await get_current_mapping(client, index_name)
        properties = mapping.get("properties", {})
        
        required_fields = [
            "execution_mode",
            "agent_decisions",
            "tool_invocations",
            "fallback_reason"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in properties:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Migration verification failed. Missing fields: {missing_fields}")
            return False
        
        logger.info("Migration verification successful. All fields present.")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying migration: {e}", exc_info=True)
        return False


async def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("Queries Index Extension Migration")
    logger.info("Feature: 001-agentic-query")
    logger.info("=" * 80)
    
    # Create OpenSearch client
    try:
        client = OpenSearch(
            hosts=[{
                "host": settings.OPENSEARCH_HOST,
                "port": settings.OPENSEARCH_PORT
            }],
            http_auth=(settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD),
            use_ssl=settings.OPENSEARCH_USE_SSL,
            verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
            ssl_show_warn=False,
            timeout=30
        )
        
        # Test connection
        info = client.info()
        logger.info(f"Connected to OpenSearch {info['version']['number']}")
        
    except Exception as e:
        logger.error(f"Failed to connect to OpenSearch: {e}")
        return 1
    
    # Extend the index
    success = await extend_index_mapping(client, QUERIES_INDEX)
    if not success:
        logger.error("Migration failed")
        return 1
    
    # Verify the migration
    verified = await verify_migration(client, QUERIES_INDEX)
    if not verified:
        logger.error("Migration verification failed")
        return 1
    
    logger.info("=" * 80)
    logger.info("Migration completed successfully")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

# Made with Bob
