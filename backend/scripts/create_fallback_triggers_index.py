#!/usr/bin/env python3
"""
Migration script to create fallback_triggers index.

This script creates a new index to track when and why the agentic query
system falls back to OpenSearch (Feature: 001-agentic-query).

The fallback_triggers index stores:
- When fallback occurred
- Why fallback was triggered
- Agent state at fallback time
- Confidence score at fallback
- Time elapsed before fallback

This data is used for:
- Monitoring agentic workflow reliability
- Identifying improvement opportunities
- Analytics and reporting

Usage:
    python backend/scripts/create_fallback_triggers_index.py
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
FALLBACK_TRIGGERS_INDEX = "fallback_triggers"

# Index settings
INDEX_SETTINGS = {
    "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "index": {
            "max_result_window": 10000
        }
    },
    "mappings": {
        "properties": {
            "trigger_id": {
                "type": "keyword"
            },
            "query_id": {
                "type": "keyword"
            },
            "session_id": {
                "type": "keyword"
            },
            "reason": {
                "type": "keyword",
                "ignore_above": 256
            },
            "agent_state": {
                "type": "object",
                "enabled": False,
                "doc_values": False
            },
            "confidence_score": {
                "type": "float"
            },
            "elapsed_time_ms": {
                "type": "integer"
            },
            "timestamp": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis"
            },
            "metadata": {
                "type": "object",
                "enabled": False,
                "doc_values": False
            }
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


async def create_index(client: OpenSearch, index_name: str) -> bool:
    """
    Create the fallback_triggers index.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Creating {index_name} index...")
        
        # Check if index already exists
        if await check_index_exists(client, index_name):
            logger.warning(f"Index {index_name} already exists")
            
            # Get current mapping
            response = client.indices.get_mapping(index=index_name)
            current_mapping = response[index_name]["mappings"]
            
            logger.info("Verifying index structure...")
            required_fields = [
                "trigger_id", "query_id", "session_id", "reason",
                "agent_state", "confidence_score", "elapsed_time_ms",
                "timestamp", "metadata"
            ]
            
            existing_properties = current_mapping.get("properties", {})
            missing_fields = [f for f in required_fields if f not in existing_properties]
            
            if missing_fields:
                logger.error(f"Index exists but is missing fields: {missing_fields}")
                logger.info("Please delete the index and run this script again")
                return False
            
            logger.info("Index structure verified")
            return True
        
        # Create the index
        client.indices.create(
            index=index_name,
            body=INDEX_SETTINGS
        )
        
        logger.info(f"Successfully created {index_name} index")
        logger.info("Index configuration:")
        logger.info(f"  - Shards: {INDEX_SETTINGS['settings']['number_of_shards']}")
        logger.info(f"  - Replicas: {INDEX_SETTINGS['settings']['number_of_replicas']}")
        logger.info(f"  - Refresh interval: {INDEX_SETTINGS['settings']['refresh_interval']}")
        logger.info("Fields:")
        for field_name in INDEX_SETTINGS["mappings"]["properties"].keys():
            logger.info(f"  - {field_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating index: {e}", exc_info=True)
        return False


async def verify_index(client: OpenSearch, index_name: str) -> bool:
    """
    Verify that the index was created successfully.
    
    Returns:
        True if index exists and has correct structure, False otherwise
    """
    try:
        logger.info("Verifying index creation...")
        
        # Check existence
        if not await check_index_exists(client, index_name):
            logger.error(f"Index {index_name} does not exist")
            return False
        
        # Get mapping
        response = client.indices.get_mapping(index=index_name)
        mapping = response[index_name]["mappings"]
        properties = mapping.get("properties", {})
        
        # Verify required fields
        required_fields = [
            "trigger_id", "query_id", "session_id", "reason",
            "agent_state", "confidence_score", "elapsed_time_ms",
            "timestamp", "metadata"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in properties:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"Verification failed. Missing fields: {missing_fields}")
            return False
        
        # Get settings
        response = client.indices.get_settings(index=index_name)
        settings = response[index_name]["settings"]["index"]
        
        logger.info("Index verification successful")
        logger.info(f"  - Shards: {settings.get('number_of_shards')}")
        logger.info(f"  - Replicas: {settings.get('number_of_replicas')}")
        logger.info(f"  - Fields: {len(properties)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying index: {e}", exc_info=True)
        return False


async def create_index_alias(client: OpenSearch, index_name: str) -> bool:
    """
    Create an alias for the fallback_triggers index.
    
    This allows for easier index rotation in the future.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        alias_name = f"{index_name}_current"
        
        logger.info(f"Creating alias {alias_name} -> {index_name}...")
        
        # Check if alias already exists
        if client.indices.exists_alias(name=alias_name):
            logger.warning(f"Alias {alias_name} already exists")
            return True
        
        # Create alias
        client.indices.put_alias(
            index=index_name,
            name=alias_name
        )
        
        logger.info(f"Successfully created alias {alias_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating alias: {e}", exc_info=True)
        return False


async def main():
    """Main migration function."""
    logger.info("=" * 80)
    logger.info("Fallback Triggers Index Creation")
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
    
    # Create the index
    success = await create_index(client, FALLBACK_TRIGGERS_INDEX)
    if not success:
        logger.error("Index creation failed")
        return 1
    
    # Verify the index
    verified = await verify_index(client, FALLBACK_TRIGGERS_INDEX)
    if not verified:
        logger.error("Index verification failed")
        return 1
    
    # Create alias
    alias_created = await create_index_alias(client, FALLBACK_TRIGGERS_INDEX)
    if not alias_created:
        logger.warning("Alias creation failed, but index is usable")
    
    logger.info("=" * 80)
    logger.info("Migration completed successfully")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

# Made with Bob
