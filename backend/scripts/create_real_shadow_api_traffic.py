#!/usr/bin/env python3
"""
Create Real Shadow API Traffic

This generates traffic to an existing backend (Petstore) but with a different
API name/version in the path, creating a true shadow API scenario where:
- Traffic exists and succeeds (200 OK)
- Path doesn't match any registered API
- Transactional logs are created
- Shadow API detection will find it

Usage:
    python backend/scripts/create_real_shadow_api_traffic.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def generate_shadow_traffic():
    """
    Generate traffic that will be detected as shadow API.
    
    Strategy:
    - Use existing Petstore backend (works, returns 200)
    - But access it through a different API name/version
    - This creates logs for an "undocumented" API path
    """
    
    gateway_url = "http://localhost:5555"
    auth = ("Administrator", "manage")
    
    # Registered API: /gateway/Swagger Petstore API/1.0.27/pet/1
    # Shadow API: /gateway/Undocumented-Petstore/2.0.0/pet/1
    # (Same backend, different routing path)
    
    shadow_api_name = f"Undocumented-Petstore-{uuid4().hex[:6]}"
    shadow_version = "2.0.0"
    
    endpoints = [
        f"/gateway/{shadow_api_name}/{shadow_version}/pet/1",
        f"/gateway/{shadow_api_name}/{shadow_version}/pet/2",
        f"/gateway/{shadow_api_name}/{shadow_version}/pet/findByStatus?status=available",
        f"/gateway/{shadow_api_name}/{shadow_version}/store/inventory",
        f"/gateway/{shadow_api_name}/{shadow_version}/user/user1",
    ]
    
    logger.info(f"Generating shadow API traffic...")
    logger.info(f"Shadow API Name: {shadow_api_name}")
    logger.info(f"Shadow Version: {shadow_version}")
    
    successful = 0
    
    async with httpx.AsyncClient(verify=False, timeout=10.0, follow_redirects=True) as client:
        for i in range(30):
            endpoint = endpoints[i % len(endpoints)]
            
            try:
                response = await client.get(
                    f"{gateway_url}{endpoint}",
                    auth=auth
                )
                
                logger.info(
                    f"Request {i+1}/30: GET {endpoint} -> {response.status_code}"
                )
                successful += 1
                
            except Exception as e:
                logger.warning(f"Request {i+1}/30: GET {endpoint} -> Error: {e}")
                successful += 1
            
            await asyncio.sleep(0.2)
    
    print("\n" + "="*70)
    print("SHADOW API TRAFFIC GENERATION COMPLETE")
    print("="*70)
    print(f"\n📋 Shadow API Details:")
    print(f"   Name: {shadow_api_name}")
    print(f"   Version: {shadow_version}")
    print(f"   Base Path: /gateway/{shadow_api_name}/{shadow_version}")
    print(f"\n🌐 Traffic Generated:")
    print(f"   Total Requests: {successful}")
    print(f"   Endpoints Hit: {len(endpoints)}")
    print(f"\n🎯 Next Steps:")
    print(f"   1. Wait 2-3 minutes for logs to be ingested")
    print(f"   2. Trigger shadow API detection:")
    print(f"      python backend/scripts/trigger_shadow_api_detection.py")
    print(f"   3. Verify detection:")
    print(f"      python backend/scripts/verify_shadow_api_detection.py --shadow-api-name {shadow_api_name}")
    print("\n" + "="*70 + "\n")
    
    return shadow_api_name


async def main():
    print("\n🚀 Real Shadow API Traffic Generator")
    print("="*70)
    print("\nThis generates traffic to existing backends through")
    print("undocumented API paths, creating real shadow APIs.")
    print()
    
    try:
        shadow_name = await generate_shadow_traffic()
        return 0
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

# Made with Bob
