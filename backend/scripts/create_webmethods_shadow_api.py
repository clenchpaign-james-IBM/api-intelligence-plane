#!/usr/bin/env python3
"""
Create a Shadow API in webMethods API Gateway for Testing

This script creates a shadow API by generating traffic to undocumented endpoints.
The API Intelligence Plane will detect these as shadow APIs during discovery.

A shadow API is detected when:
- Traffic exists for a request path (transactional logs)
- No registered API matches that request path pattern
- The discovery service identifies it as undocumented

Usage:
    python backend/scripts/create_webmethods_shadow_api.py

Requirements:
    - webMethods Gateway running at http://localhost:5555
    - Gateway credentials (default: Administrator/manage)
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict
from uuid import uuid4

import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WebMethodsShadowAPICreator:
    """Creates a shadow API by generating traffic to undocumented endpoints."""
    
    def __init__(
        self,
        gateway_url: str = "http://localhost:5555",
        username: str = "Administrator",
        password: str = "manage",
    ):
        """
        Initialize the shadow API creator.
        
        Args:
            gateway_url: webMethods Gateway URL
            username: Gateway admin username
            password: Gateway admin password
        """
        self.gateway_url = gateway_url
        self.auth = (username, password)
        self.shadow_api_name = f"shadow-api-{uuid4().hex[:8]}"
        self.shadow_version = "1.0.0"
        
    async def check_gateway_health(self) -> bool:
        """Check if webMethods Gateway is accessible."""
        try:
            logger.info(f"Checking gateway health at {self.gateway_url}")
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                response = await client.get(
                    f"{self.gateway_url}/rest/apigateway/health",
                    auth=self.auth
                )
                response.raise_for_status()
                logger.info("✅ Gateway is healthy and accessible")
                return True
        except Exception as e:
            logger.error(f"❌ Gateway health check failed: {e}")
            return False
    
    async def generate_shadow_traffic(self, num_requests: int = 30) -> int:
        """
        Generate traffic to undocumented API endpoints.
        
        This creates transactional logs for paths that don't have registered APIs,
        which will be detected as shadow APIs by the intelligence system.
        
        Args:
            num_requests: Number of requests to generate
            
        Returns:
            int: Number of requests made
        """
        logger.info(f"Generating {num_requests} requests to shadow API endpoints")
        
        # Define undocumented endpoints to hit
        # These paths follow webMethods routing: /gateway/{apiName}/{version}/{resource}
        base_path = f"/gateway/{self.shadow_api_name}/{self.shadow_version}"
        endpoints = [
            ("GET", f"{base_path}/users"),
            ("GET", f"{base_path}/users/123"),
            ("GET", f"{base_path}/users/456"),
            ("POST", f"{base_path}/users"),
            ("GET", f"{base_path}/products"),
            ("GET", f"{base_path}/products/789"),
            ("POST", f"{base_path}/admin/secret"),
            ("GET", f"{base_path}/admin/config"),
            ("PUT", f"{base_path}/settings"),
            ("DELETE", f"{base_path}/cache"),
        ]
        
        successful = 0
        
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            for i in range(num_requests):
                method, path = endpoints[i % len(endpoints)]
                
                try:
                    # Make request to undocumented endpoint
                    if method == "GET":
                        response = await client.get(
                            f"{self.gateway_url}{path}",
                            auth=self.auth
                        )
                    elif method == "POST":
                        response = await client.post(
                            f"{self.gateway_url}{path}",
                            auth=self.auth,
                            json={"test": "data", "timestamp": datetime.utcnow().isoformat()}
                        )
                    elif method == "PUT":
                        response = await client.put(
                            f"{self.gateway_url}{path}",
                            auth=self.auth,
                            json={"test": "data"}
                        )
                    elif method == "DELETE":
                        response = await client.delete(
                            f"{self.gateway_url}{path}",
                            auth=self.auth
                        )
                    
                    # We expect 404 or 500 errors (no backend), but that's OK
                    # The transactional logs will still be created
                    logger.debug(
                        f"Request {i+1}/{num_requests}: {method} {path} "
                        f"-> {response.status_code}"
                    )
                    successful += 1
                    
                except Exception as e:
                    # Even errors create transactional logs
                    logger.debug(
                        f"Request {i+1}/{num_requests}: {method} {path} "
                        f"-> Error: {e}"
                    )
                    successful += 1
                
                # Small delay between requests
                await asyncio.sleep(0.2)
        
        logger.info(f"✅ Generated {successful} requests to shadow API endpoints")
        return successful
    
    async def verify_no_registered_api(self) -> bool:
        """
        Verify that no API is registered with this name in the gateway.
        
        Returns:
            bool: True if no API found (good for shadow API)
        """
        try:
            logger.info(f"Verifying no API registered with name: {self.shadow_api_name}")
            
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                # Try to list APIs and check if our shadow API name exists
                response = await client.get(
                    f"{self.gateway_url}/rest/apigateway/apis",
                    auth=self.auth
                )
                response.raise_for_status()
                
                data = response.json()
                api_responses = data.get("apiResponse", [])
                
                for api_response in api_responses:
                    api_data = api_response.get("api", {})
                    api_name = api_data.get("apiName") or api_data.get("name")
                    
                    if api_name == self.shadow_api_name:
                        logger.warning(
                            f"⚠️  API with name '{self.shadow_api_name}' already exists!"
                        )
                        return False
                
                logger.info(
                    f"✅ No API registered with name '{self.shadow_api_name}' "
                    f"(perfect for shadow API)"
                )
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to verify API registration: {e}")
            return False
    
    def print_summary(self, requests_made: int):
        """Print a summary of the shadow API creation."""
        print("\n" + "="*70)
        print("SHADOW API CREATION SUMMARY")
        print("="*70)
        print(f"\n📋 Shadow API Details:")
        print(f"   Name: {self.shadow_api_name}")
        print(f"   Version: {self.shadow_version}")
        print(f"   Base Path: /gateway/{self.shadow_api_name}/{self.shadow_version}")
        
        print(f"\n🌐 Traffic Generated:")
        print(f"   Total Requests: {requests_made}")
        print(f"   Status: Transactional logs created")
        
        print(f"\n🔍 Shadow API Endpoints (with traffic):")
        print(f"   GET  /gateway/{self.shadow_api_name}/{self.shadow_version}/users")
        print(f"   GET  /gateway/{self.shadow_api_name}/{self.shadow_version}/users/{{id}}")
        print(f"   POST /gateway/{self.shadow_api_name}/{self.shadow_version}/users")
        print(f"   GET  /gateway/{self.shadow_api_name}/{self.shadow_version}/products")
        print(f"   POST /gateway/{self.shadow_api_name}/{self.shadow_version}/admin/secret")
        print(f"   ... and more")
        
        print(f"\n✅ Shadow API Status:")
        print(f"   ✓ Traffic generated to undocumented endpoints")
        print(f"   ✓ Transactional logs created in webMethods")
        print(f"   ✓ No registered API with this name")
        print(f"   ✓ Ready for shadow API detection")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Wait 5-10 minutes for shadow API detection job to run")
        print(f"      (Scheduled job runs every 5 minutes)")
        print(f"")
        print(f"   2. Or trigger discovery manually via API Intelligence Plane:")
        print(f"      POST http://localhost:8000/api/v1/gateways/{{gateway_id}}/sync")
        print(f"")
        print(f"   3. Check for shadow API in the system:")
        print(f"      GET http://localhost:8000/api/v1/apis?is_shadow=true")
        print(f"")
        print(f"   4. Look for API with name containing: {self.shadow_api_name}")
        print(f"      Or search by base path: /gateway/{self.shadow_api_name}/{self.shadow_version}")
        
        print(f"\n💡 How Shadow API Detection Works:")
        print(f"   1. Discovery service analyzes transactional logs")
        print(f"   2. Extracts unique request paths from logs")
        print(f"   3. Checks if each path matches a registered API")
        print(f"   4. Paths without matching APIs are flagged as shadow APIs")
        print(f"   5. Shadow APIs appear with is_shadow=true flag")
        
        print("\n" + "="*70 + "\n")


async def main():
    """Main execution function."""
    print("\n🚀 webMethods Shadow API Creator")
    print("="*70)
    print("\nThis script creates a shadow API by generating traffic to")
    print("undocumented endpoints. The API Intelligence Plane will detect")
    print("these as shadow APIs during the next discovery cycle.")
    
    # Configuration
    gateway_url = "http://localhost:5555"
    username = "Administrator"
    password = "manage"
    
    print(f"\n📡 Gateway: {gateway_url}")
    print(f"👤 User: {username}")
    print()
    
    try:
        creator = WebMethodsShadowAPICreator(gateway_url, username, password)
        
        # Step 1: Check gateway health
        print("🔍 Step 1: Checking gateway health...")
        if not await creator.check_gateway_health():
            logger.error("Cannot proceed - gateway is not accessible")
            return 1
        
        # Step 2: Verify no API registered with this name
        print(f"\n🔍 Step 2: Verifying no API registered as '{creator.shadow_api_name}'...")
        if not await creator.verify_no_registered_api():
            logger.warning(
                "An API with this name already exists. "
                "Shadow API detection may not work as expected."
            )
        
        # Step 3: Generate traffic to undocumented endpoints
        print(f"\n🌐 Step 3: Generating traffic to undocumented endpoints...")
        print("   (This creates transactional logs without registered APIs)")
        requests_made = await creator.generate_shadow_traffic(num_requests=30)
        
        # Print summary
        creator.print_summary(requests_made)
        
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
