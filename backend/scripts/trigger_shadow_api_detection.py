#!/usr/bin/env python3
"""
Manually Trigger Shadow API Detection Job

This script manually runs the shadow API detection job to immediately
detect shadow APIs without waiting for the scheduled job.

Usage:
    python backend/scripts/trigger_shadow_api_detection.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scheduler.intelligence_metadata_jobs import detect_shadow_apis_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main execution function."""
    print("\n🔍 Manual Shadow API Detection")
    print("="*70)
    print("\nThis script manually triggers the shadow API detection job")
    print("to immediately detect shadow APIs from transactional logs.")
    print()
    
    try:
        logger.info("Starting shadow API detection job...")
        await detect_shadow_apis_job()
        logger.info("✅ Shadow API detection job completed")
        
        print("\n" + "="*70)
        print("SHADOW API DETECTION COMPLETE")
        print("="*70)
        print("\n🎯 Next Steps:")
        print("   1. Check for shadow APIs:")
        print("      python backend/scripts/verify_shadow_api_detection.py --shadow-api-name shadow-api-ee463658")
        print("\n   2. Or query directly:")
        print("      curl 'http://localhost:8000/api/v1/apis?is_shadow=true'")
        print("\n" + "="*70 + "\n")
        
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
