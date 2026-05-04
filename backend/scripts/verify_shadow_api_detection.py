#!/usr/bin/env python3
"""
Verify Shadow API Detection in API Intelligence Plane

This script:
1. Triggers discovery/sync for the webMethods gateway
2. Checks for shadow APIs in the system
3. Verifies the shadow API created by create_webmethods_shadow_api.py

Usage:
    python backend/scripts/verify_shadow_api_detection.py [--shadow-api-name shadow-api-ee463658]
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ShadowAPIVerifier:
    """Verifies shadow API detection in the API Intelligence Plane."""
    
    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        shadow_api_name: Optional[str] = None,
    ):
        """
        Initialize the verifier.
        
        Args:
            backend_url: API Intelligence Plane backend URL
            shadow_api_name: Optional specific shadow API name to look for
        """
        self.backend_url = backend_url
        self.shadow_api_name = shadow_api_name
        
    async def get_gateways(self) -> List[Dict]:
        """Get all registered gateways."""
        try:
            logger.info("Fetching registered gateways...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/v1/gateways")
                response.raise_for_status()
                
                data = response.json()
                # API returns {"items": [...], "total": N, ...}
                gateways = data.get("items", [])
                
                logger.info(f"✅ Found {len(gateways)} registered gateway(s)")
                return gateways
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch gateways: {e}")
            return []
    
    async def trigger_gateway_sync(self, gateway_id: str) -> bool:
        """
        Trigger discovery/sync for a specific gateway.
        
        Args:
            gateway_id: Gateway UUID
            
        Returns:
            bool: True if sync triggered successfully
        """
        try:
            logger.info(f"Triggering sync for gateway {gateway_id}...")
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/v1/gateways/{gateway_id}/sync"
                )
                response.raise_for_status()
                
                result = response.json()
                apis_discovered = result.get("apis_discovered", 0)
                shadow_apis = result.get("shadow_apis_found", 0)
                
                logger.info(f"✅ Sync completed:")
                logger.info(f"   APIs discovered: {apis_discovered}")
                logger.info(f"   Shadow APIs found: {shadow_apis}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to trigger sync: {e}")
            return False
    
    async def get_shadow_apis(self) -> List[Dict]:
        """Get all shadow APIs from the system."""
        try:
            logger.info("Fetching shadow APIs...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/v1/apis",
                    params={"is_shadow": "true", "page_size": 100}
                )
                response.raise_for_status()
                
                data = response.json()
                apis = data.get("apis", [])
                
                logger.info(f"✅ Found {len(apis)} shadow API(s)")
                return apis
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch shadow APIs: {e}")
            return []
    
    async def find_specific_shadow_api(self, apis: List[Dict]) -> Optional[Dict]:
        """
        Find a specific shadow API by name.
        
        Args:
            apis: List of API objects
            
        Returns:
            API object if found, None otherwise
        """
        if not self.shadow_api_name:
            return None
        
        for api in apis:
            name = api.get("name", "")
            if self.shadow_api_name in name:
                logger.info(f"✅ Found shadow API: {name}")
                return api
        
        logger.warning(f"⚠️  Shadow API with name containing '{self.shadow_api_name}' not found")
        return None
    
    def print_shadow_api_details(self, api: Dict):
        """Print detailed information about a shadow API."""
        print("\n" + "="*70)
        print("SHADOW API DETAILS")
        print("="*70)
        
        print(f"\n📋 Basic Information:")
        print(f"   ID: {api.get('id')}")
        print(f"   Name: {api.get('name')}")
        print(f"   Display Name: {api.get('display_name')}")
        print(f"   Version: {api.get('version_info', {}).get('current_version')}")
        print(f"   Base Path: {api.get('base_path')}")
        
        print(f"\n🔍 Shadow API Metadata:")
        intel = api.get('intelligence_metadata', {})
        print(f"   Is Shadow: {intel.get('is_shadow')}")
        print(f"   Discovery Method: {intel.get('discovery_method')}")
        print(f"   Discovered At: {intel.get('discovered_at')}")
        print(f"   Last Seen At: {intel.get('last_seen_at')}")
        print(f"   Health Score: {intel.get('health_score')}")
        print(f"   Risk Score: {intel.get('risk_score')}")
        
        print(f"\n🌐 Endpoints:")
        endpoints = api.get('endpoints', [])
        if endpoints:
            for endpoint in endpoints[:5]:  # Show first 5
                print(f"   {endpoint.get('method')} {endpoint.get('path')}")
            if len(endpoints) > 5:
                print(f"   ... and {len(endpoints) - 5} more")
        else:
            print(f"   No endpoints defined")
        
        print(f"\n📊 Status:")
        print(f"   API Status: {api.get('status')}")
        print(f"   Is Active: {api.get('is_active')}")
        print(f"   Gateway ID: {api.get('gateway_id')}")
        
        print("\n" + "="*70 + "\n")
    
    def print_summary(self, gateways: List[Dict], shadow_apis: List[Dict], found_api: Optional[Dict]):
        """Print verification summary."""
        print("\n" + "="*70)
        print("SHADOW API DETECTION VERIFICATION SUMMARY")
        print("="*70)
        
        print(f"\n📊 System Status:")
        print(f"   Registered Gateways: {len(gateways)}")
        print(f"   Total Shadow APIs: {len(shadow_apis)}")
        
        if self.shadow_api_name:
            print(f"\n🎯 Target Shadow API:")
            print(f"   Looking for: {self.shadow_api_name}")
            print(f"   Found: {'✅ Yes' if found_api else '❌ No'}")
        
        if shadow_apis:
            print(f"\n🔍 All Shadow APIs:")
            for api in shadow_apis:
                name = api.get('name', 'Unknown')
                base_path = api.get('base_path', 'N/A')
                print(f"   • {name}")
                print(f"     Base Path: {base_path}")
                print(f"     Discovery: {api.get('intelligence_metadata', {}).get('discovery_method')}")
        
        print(f"\n✅ Verification Complete!")
        
        if found_api:
            print(f"\n💡 Next Steps:")
            print(f"   1. Review shadow API details above")
            print(f"   2. Investigate why this API is undocumented")
            print(f"   3. Consider registering it properly or blocking access")
            print(f"   4. Monitor for security risks")
        elif self.shadow_api_name:
            print(f"\n⚠️  Shadow API Not Detected Yet:")
            print(f"   1. Wait a few more minutes for detection job to run")
            print(f"   2. Check transactional logs in webMethods")
            print(f"   3. Verify gateway sync completed successfully")
            print(f"   4. Re-run this script to check again")
        
        print("\n" + "="*70 + "\n")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Verify shadow API detection in API Intelligence Plane"
    )
    parser.add_argument(
        "--shadow-api-name",
        help="Specific shadow API name to look for (e.g., shadow-api-ee463658)",
        default=None
    )
    parser.add_argument(
        "--backend-url",
        help="API Intelligence Plane backend URL",
        default="http://localhost:8000"
    )
    
    args = parser.parse_args()
    
    print("\n🔍 Shadow API Detection Verifier")
    print("="*70)
    print(f"\n📡 Backend: {args.backend_url}")
    if args.shadow_api_name:
        print(f"🎯 Target: {args.shadow_api_name}")
    print()
    
    try:
        verifier = ShadowAPIVerifier(args.backend_url, args.shadow_api_name)
        
        # Step 1: Get gateways
        print("📋 Step 1: Fetching registered gateways...")
        gateways = await verifier.get_gateways()
        
        if not gateways:
            logger.error("No gateways found. Please register a gateway first.")
            return 1
        
        # Step 2: Trigger sync for each gateway
        print(f"\n🔄 Step 2: Triggering sync for {len(gateways)} gateway(s)...")
        for gateway in gateways:
            gateway_id = gateway.get("id")
            gateway_name = gateway.get("name")
            print(f"\n   Syncing gateway: {gateway_name} ({gateway_id})")
            await verifier.trigger_gateway_sync(gateway_id)
            await asyncio.sleep(2)  # Brief delay between syncs
        
        # Step 3: Get shadow APIs
        print(f"\n🔍 Step 3: Fetching shadow APIs...")
        shadow_apis = await verifier.get_shadow_apis()
        
        # Step 4: Find specific shadow API if name provided
        found_api = None
        if args.shadow_api_name:
            print(f"\n🎯 Step 4: Looking for shadow API: {args.shadow_api_name}...")
            found_api = await verifier.find_specific_shadow_api(shadow_apis)
            
            if found_api:
                verifier.print_shadow_api_details(found_api)
        
        # Print summary
        verifier.print_summary(gateways, shadow_apis, found_api)
        
        return 0 if (not args.shadow_api_name or found_api) else 1
        
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
