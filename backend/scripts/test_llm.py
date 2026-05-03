"""LLM testing script for API Intelligence Plane.

Tests LLM provider connections and validates LLM service functionality.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.config import Settings
from backend.app.services.llm_service import LLMService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_provider_connections(llm_service: LLMService) -> None:
    """Test connections to all configured LLM providers.

    Args:
        llm_service: LLM service instance
    """
    logger.info("Testing LLM provider connections...")
    print("\n" + "=" * 60)
    print("LLM PROVIDER CONNECTION TEST")
    print("=" * 60)

    results = await llm_service.test_connection()

    print(f"\nTotal Providers Configured: {results['total_providers']}")
    print("\nProvider Test Results:")
    print("-" * 60)

    for result in results["results"]:
        status_symbol = "✓" if result["status"] == "success" else "✗"
        print(f"\n{status_symbol} {result['model']}")
        print(f"  Status: {result['status']}")

        if result["status"] == "success":
            print(f"  Response: {result['response']}")
        else:
            print(f"  Error: {result['error']}")

    print("\n" + "=" * 60)


async def test_query_interpretation(llm_service: LLMService) -> None:
    """Test natural language query interpretation.

    Args:
        llm_service: LLM service instance
    """
    logger.info("Testing query interpretation...")
    print("\n" + "=" * 60)
    print("QUERY INTERPRETATION TEST")
    print("=" * 60)

    test_queries = [
        "Show me all critical vulnerabilities in the last week",
        "What APIs have the highest error rates?",
        "Predict which APIs might fail in the next 24 hours",
        "Compare response times between user-api and payment-api",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)

        try:
            intent = await llm_service.interpret_query(query)
            print(f"Action: {intent.get('action')}")
            print(f"Entities: {intent.get('entities')}")
            print(f"Filters: {intent.get('filters')}")
            if intent.get("time_range"):
                print(f"Time Range: {intent.get('time_range')}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "=" * 60)


async def test_prediction_explanation(llm_service: LLMService) -> None:
    """Test prediction explanation generation.

    Args:
        llm_service: LLM service instance
    """
    logger.info("Testing prediction explanation...")
    print("\n" + "=" * 60)
    print("PREDICTION EXPLANATION TEST")
    print("=" * 60)

    prediction_data = {
        "prediction_type": "failure",
        "confidence_score": 0.85,
        "severity": "high",
        "contributing_factors": [
            {
                "factor": "increasing_error_rate",
                "current_value": 0.15,
                "threshold": 0.10,
                "trend": "increasing",
                "weight": 0.35,
            },
            {
                "factor": "degrading_response_time",
                "current_value": 350.0,
                "threshold": 200.0,
                "trend": "increasing",
                "weight": 0.25,
            },
        ],
        "recommended_actions": [
            "Scale up API instances",
            "Review recent code changes",
            "Check database connection pool",
        ],
    }

    print("\nPrediction Data:")
    print(f"  Type: {prediction_data['prediction_type']}")
    print(f"  Confidence: {prediction_data['confidence_score'] * 100:.1f}%")
    print(f"  Severity: {prediction_data['severity']}")
    print("\nGenerating explanation...")
    print("-" * 60)

    try:
        explanation = await llm_service.generate_prediction_explanation(prediction_data)
        print(f"\nExplanation:\n{explanation}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)


async def test_optimization_recommendation(llm_service: LLMService) -> None:
    """Test optimization recommendation generation.

    Args:
        llm_service: LLM service instance
    """
    logger.info("Testing optimization recommendation...")
    print("\n" + "=" * 60)
    print("OPTIMIZATION RECOMMENDATION TEST")
    print("=" * 60)

    api_metrics = {
        "response_time_p95": 250.0,
        "response_time_p99": 450.0,
        "error_rate": 0.05,
        "throughput": 150.0,
        "availability": 98.5,
    }

    print("\nAPI Metrics:")
    print(f"  Response Time P95: {api_metrics['response_time_p95']}ms")
    print(f"  Response Time P99: {api_metrics['response_time_p99']}ms")
    print(f"  Error Rate: {api_metrics['error_rate'] * 100:.2f}%")
    print(f"  Throughput: {api_metrics['throughput']} req/s")
    print(f"  Availability: {api_metrics['availability']}%")
    print("\nGenerating recommendation...")
    print("-" * 60)

    try:
        recommendation = await llm_service.generate_optimization_recommendation(api_metrics)
        print(f"\nRecommendation Type: {recommendation.get('recommendation_type')}")
        print(f"Title: {recommendation.get('title')}")
        print(f"Priority: {recommendation.get('priority')}")
        print(f"\nDescription:\n{recommendation.get('description')}")
        if recommendation.get("implementation_steps"):
            print("\nImplementation Steps:")
            for i, step in enumerate(recommendation.get("implementation_steps", []), 1):
                print(f"  {i}. {step}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)


async def test_basic_completion(llm_service: LLMService) -> None:
    """Test basic LLM completion.

    Args:
        llm_service: LLM service instance
    """
    logger.info("Testing basic completion...")
    print("\n" + "=" * 60)
    print("BASIC COMPLETION TEST")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "Explain what an API Gateway is in one sentence."}
    ]

    print("\nPrompt: Explain what an API Gateway is in one sentence.")
    print("-" * 60)

    try:
        response = await llm_service.generate_completion(messages, temperature=0.5, max_tokens=100)
        print(f"\nModel: {response['model']}")
        print(f"Response: {response['content']}")
        print(f"\nUsage:")
        print(f"  Prompt Tokens: {response['usage']['prompt_tokens']}")
        print(f"  Completion Tokens: {response['usage']['completion_tokens']}")
        print(f"  Total Tokens: {response['usage']['total_tokens']}")
        print(f"  Estimated Cost: ${response['cost']:.6f}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)


async def main() -> None:
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test LLM provider connections")
    parser.add_argument(
        "--test",
        choices=["all", "connection", "query", "prediction", "optimization", "completion"],
        default="all",
        help="Which test to run (default: all)",
    )
    args = parser.parse_args()

    # Load settings
    settings = Settings()

    # Initialize LLM service
    llm_service = LLMService(settings)

    if not llm_service.providers:
        logger.error("No LLM providers configured. Please set API keys in .env file.")
        print("\n❌ No LLM providers configured!")
        print("\nPlease configure at least one LLM provider in your .env file:")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        print("  - GOOGLE_API_KEY")
        print("  - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT")
        print("  - WATSONX_API_KEY + WATSONX_URL + WATSONX_PROJECT_ID")
        print("  - OLLAMA_BASE_URL")
        return

    # Run tests
    try:
        if args.test in ["all", "connection"]:
            await test_provider_connections(llm_service)

        if args.test in ["all", "completion"]:
            await test_basic_completion(llm_service)

        if args.test in ["all", "query"]:
            await test_query_interpretation(llm_service)

        if args.test in ["all", "prediction"]:
            await test_prediction_explanation(llm_service)

        if args.test in ["all", "optimization"]:
            await test_optimization_recommendation(llm_service)

        print("\n✓ All tests completed!")

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
