#!/usr/bin/env python3
"""
Check if shadow API traffic created transactional logs in OpenSearch.
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.client import get_opensearch_client


def check_logs():
    """Check for shadow API logs in OpenSearch."""
    os_client = get_opensearch_client()
    client = os_client.client
    
    print("\n" + "="*70)
    print("CHECKING SHADOW API LOGS IN OPENSEARCH")
    print("="*70)
    
    # Search for logs with the shadow API name
    shadow_api_name = "Undocumented-Petstore-76b56c"
    
    try:
        # Query 1: Search by API name
        print(f"\n🔍 Searching for logs with apiName: {shadow_api_name}")
        response = client.search(
            index="gateway_default_analytics",
            body={
                "size": 5,
                "query": {
                    "match": {
                        "apiName": shadow_api_name
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        )
        
        hits = response.get("hits", {}).get("hits", [])
        print(f"   Found {len(hits)} logs")
        
        if hits:
            print("\n📋 Sample Log Entry:")
            log = hits[0]["_source"]
            print(f"   API Name: {log.get('apiName')}")
            print(f"   API Version: {log.get('apiVersion')}")
            print(f"   Request Path: {log.get('requestPath')}")
            print(f"   HTTP Method: {log.get('httpMethod')}")
            print(f"   Status Code: {log.get('statusCode')}")
            print(f"   Timestamp: {log.get('@timestamp')}")
        
        # Query 2: Get recent logs (last 10 minutes)
        print(f"\n🔍 Searching for ALL recent logs (last 10 minutes)")
        response2 = client.search(
            index="gateway_default_analytics",
            body={
                "size": 10,
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": "now-10m"
                        }
                    }
                },
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        )
        
        hits2 = response2.get("hits", {}).get("hits", [])
        print(f"   Found {len(hits2)} recent logs")
        
        if hits2:
            print("\n📋 Recent API Names:")
            api_names = set()
            for hit in hits2:
                api_name = hit["_source"].get("apiName", "N/A")
                api_names.add(api_name)
            for name in sorted(api_names):
                print(f"   - {name}")
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        if hits:
            print(f"✅ Shadow API logs FOUND!")
            print(f"   - Logs by API name: {len(hits)}")
            print(f"\n🎯 Next Step: Trigger shadow API detection")
            print(f"   python backend/scripts/trigger_shadow_api_detection.py")
        else:
            print(f"❌ No shadow API logs found")
            print(f"\n⚠️  Possible reasons:")
            print(f"   1. Logs not yet ingested (wait 2-3 minutes)")
            print(f"   2. webMethods not logging 404 errors")
            print(f"   3. Analytics not enabled for the gateway")
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error checking logs: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_logs()

# Made with Bob
