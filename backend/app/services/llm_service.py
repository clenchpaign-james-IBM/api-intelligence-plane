"""LLM service for API Intelligence Plane.

Provides LLM integration using LiteLLM with provider fallback chain
for natural language query processing, prediction generation, and recommendations.
"""

import asyncio
import logging
from typing import Any, Optional

from litellm import acompletion, completion_cost

from app.config import Settings
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)


# Connection pool for LLM service (T087)
_connection_semaphore: Optional[asyncio.Semaphore] = None
_max_concurrent_requests = 10  # Maximum concurrent LLM requests

# Circuit breaker for LLM service (T090)
_llm_circuit_breaker: Optional[CircuitBreaker] = None


class LLMService:
    """LLM service with multi-provider support and fallback chain.

    This service uses LiteLLM to provide a unified interface to multiple
    LLM providers (OpenAI, Anthropic, Google, Azure, Ollama) with automatic
    fallback on failure.
    """

    def __init__(self, settings: Settings):
        """Initialize LLM service with configuration.

        Args:
            settings: Application settings containing LLM configuration
        """
        self.settings = settings
        self._setup_providers()
        self._init_connection_pool()
    
    def _init_connection_pool(self) -> None:
        """Initialize connection pool semaphore (T087) and circuit breaker (T090)."""
        global _connection_semaphore, _llm_circuit_breaker
        
        if _connection_semaphore is None:
            _connection_semaphore = asyncio.Semaphore(_max_concurrent_requests)
            logger.info(f"Initialized LLM connection pool with {_max_concurrent_requests} max concurrent requests")
        
        if _llm_circuit_breaker is None:
            _llm_circuit_breaker = CircuitBreaker(
                name="llm_service",
                failure_threshold=5,
                recovery_timeout=60.0,
                success_threshold=2,
            )
            logger.info("Initialized LLM circuit breaker")

    def _setup_providers(self) -> None:
        """Setup LLM provider fallback chain based on configuration."""
        self.providers = []

        # Build provider list based on enabled providers
        # OpenAI
        if getattr(self.settings, 'OPENAI_API_KEY', None):
            self.providers.append({
                "model": getattr(self.settings, 'LLM_MODEL', 'gpt-4'),
                "api_key": self.settings.OPENAI_API_KEY,
            })

        # Anthropic
        if getattr(self.settings, 'ANTHROPIC_API_KEY', None):
            self.providers.append({
                "model": getattr(self.settings, 'LLM_MODEL', 'claude-3-sonnet-20240229'),
                "api_key": self.settings.ANTHROPIC_API_KEY,
            })

        # Google
        if getattr(self.settings, 'GOOGLE_API_KEY', None):
            self.providers.append({
                "model": getattr(self.settings, 'LLM_MODEL', 'gemini-pro'),
                "api_key": self.settings.GOOGLE_API_KEY,
            })

        # Azure OpenAI
        azure_key = getattr(self.settings, 'AZURE_OPENAI_API_KEY', None)
        azure_endpoint = getattr(self.settings, 'AZURE_OPENAI_ENDPOINT', None)
        azure_deployment = getattr(self.settings, 'AZURE_OPENAI_DEPLOYMENT', None)
        if azure_key and azure_endpoint and azure_deployment:
            self.providers.append({
                "model": f"azure/{azure_deployment}",
                "api_key": azure_key,
                "api_base": azure_endpoint,
                "api_version": "2024-02-15-preview",
            })

        # IBM watsonx
        watsonx_api_key = getattr(self.settings, 'WATSONX_API_KEY', None)
        watsonx_url = getattr(self.settings, 'WATSONX_URL', None)
        watsonx_project_id = getattr(self.settings, 'WATSONX_PROJECT_ID', None)
        if watsonx_api_key and watsonx_url and watsonx_project_id:
            watsonx_model = self.settings.LLM_MODEL if self.settings.LLM_PROVIDER == "watsonx" else "ibm/granite-13b-chat-v2"
            if not watsonx_model.startswith("watsonx/"):
                watsonx_model = f"watsonx/{watsonx_model}"

            self.providers.append({
                "model": watsonx_model,
                "api_key": watsonx_api_key,
                "api_base": watsonx_url.rstrip("/"),
                "project_id": watsonx_project_id,
            })

        # Ollama (local)
        ollama_url = getattr(self.settings, 'OLLAMA_BASE_URL', None)
        if ollama_url or self.settings.LLM_PROVIDER == "ollama":
            # Use configured model or default
            ollama_model = self.settings.LLM_MODEL if self.settings.LLM_PROVIDER == "ollama" else "llama3.1:8b"
            # Ensure model has ollama/ prefix for litellm
            if not ollama_model.startswith("ollama/"):
                ollama_model = f"ollama/{ollama_model}"
            
            self.providers.append({
                "model": ollama_model,
                "api_base": ollama_url or "http://localhost:11434",
            })

        if not self.providers:
            logger.warning("No LLM providers configured. LLM features will be unavailable.")
        else:
            logger.info(f"Configured {len(self.providers)} LLM provider(s)")

    async def generate_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate LLM completion with automatic provider fallback.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt to prepend

        Returns:
            dict: Response containing:
                - content: Generated text
                - model: Model used
                - usage: Token usage statistics
                - cost: Estimated cost in USD

        Raises:
            RuntimeError: If all providers fail
        """
        if not self.providers:
            raise RuntimeError("No LLM providers configured")

        # Prepend system prompt if provided
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                logger.info(f"Attempting LLM completion with provider {i+1}/{len(self.providers)}: {provider['model']}")

                # Wrap with circuit breaker (T090) and connection pool (T087)
                async def _make_llm_call():
                    semaphore = _connection_semaphore
                    if semaphore is None:
                        raise RuntimeError("LLM connection pool not initialized")

                    async with semaphore:
                        return await acompletion(
                            model=provider["model"],
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            api_key=provider.get("api_key"),
                            api_base=provider.get("api_base"),
                            api_version=provider.get("api_version"),
                            project_id=provider.get("project_id"),
                        )

                circuit_breaker = _llm_circuit_breaker
                if circuit_breaker is None:
                    raise RuntimeError("LLM circuit breaker not initialized")

                response = await circuit_breaker.call_async(_make_llm_call)

                # Calculate cost
                cost = completion_cost(completion_response=response)

                result = {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                    "cost": cost,
                }

                logger.info(f"LLM completion successful with {provider['model']}")
                logger.info(f"LLM completion result content: {result['content']}")
                return result

            except CircuitBreakerError as e:
                last_error = e
                logger.error(f"LLM circuit breaker is OPEN: {e}")
                # Circuit breaker open - try next provider immediately
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"LLM provider {provider['model']} failed: {e}")
                continue

        # All providers failed
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    async def interpret_query(self, query_text: str) -> dict[str, Any]:
        """Interpret natural language query into structured intent.

        Args:
            query_text: Natural language query from user

        Returns:
            dict: Interpreted intent with action, entities, filters
        """
        system_prompt = """You are an API intelligence assistant. Parse the user's natural language query into structured intent.

Return a JSON object with:
- action: The action to perform (list, show, compare, analyze, predict)
- entities: List of entities involved (api, vulnerability, metric, prediction, etc.)
- filters: Dictionary of filter conditions
- time_range: Optional time range with start and end timestamps

Example:
Query: "Show me all critical vulnerabilities in the last week"
Response: {
  "action": "list",
  "entities": ["vulnerability"],
  "filters": {"severity": "critical", "status": "open"},
  "time_range": {"start": "2026-03-02T00:00:00Z", "end": "2026-03-09T23:59:59Z"}
}"""

        messages = [{"role": "user", "content": query_text}]

        response = await self.generate_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500,
        )

        # Parse JSON response
        import json
        try:
            intent = json.loads(response["content"])
            return intent
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {response['content']}")
            return {
                "action": "general",
                "entities": [],
                "filters": {},
            }

    async def generate_prediction_explanation(
        self, prediction_data: dict[str, Any]
    ) -> str:
        """Generate natural language explanation for a prediction.

        Args:
            prediction_data: Prediction data including factors and confidence

        Returns:
            str: Natural language explanation
        """
        system_prompt = """You are an API intelligence assistant. Generate a clear, concise explanation of the prediction for technical users."""

        prompt = f"""Explain this API failure prediction:

Prediction Type: {prediction_data.get('prediction_type')}
Confidence: {prediction_data.get('confidence_score', 0) * 100:.1f}%
Severity: {prediction_data.get('severity')}
Contributing Factors: {prediction_data.get('contributing_factors', [])}
Recommended Actions: {prediction_data.get('recommended_actions', [])}

Provide a 2-3 sentence explanation that is clear and actionable."""

        messages = [{"role": "user", "content": prompt}]

        response = await self.generate_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=300,
        )

        return response["content"]

    async def generate_optimization_recommendation(
        self, api_metrics: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate optimization recommendation based on API metrics.

        Args:
            api_metrics: API performance metrics

        Returns:
            dict: Optimization recommendation with type, description, and steps
        """
        system_prompt = """You are an API performance optimization expert. Analyze metrics and suggest optimizations.

Return a JSON object with:
- recommendation_type: Type of optimization (caching, query_optimization, etc.)
- title: Brief title
- description: Detailed description
- priority: Priority level (critical, high, medium, low)
- implementation_steps: List of implementation steps
- estimated_impact: Expected improvement percentage"""

        prompt = f"""Analyze these API metrics and suggest an optimization:

Response Time P95: {api_metrics.get('response_time_p95')}ms
Response Time P99: {api_metrics.get('response_time_p99')}ms
Error Rate: {api_metrics.get('error_rate', 0) * 100:.2f}%
Throughput: {api_metrics.get('throughput')} req/s
Availability: {api_metrics.get('availability')}%

Provide a specific, actionable optimization recommendation."""

        messages = [{"role": "user", "content": prompt}]

        response = await self.generate_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=800,
        )

        # Parse JSON response
        import json
        try:
            recommendation = json.loads(response["content"])
            return recommendation
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {response['content']}")
            return {
                "recommendation_type": "general",
                "title": "Performance Optimization",
                "description": response["content"],
                "priority": "medium",
                "implementation_steps": [],
                "estimated_impact": 0,
            }

    async def test_connection(self) -> dict[str, Any]:
        """Test LLM provider connections.

        Returns:
            dict: Test results for each provider
        """
        results = []

        for provider in self.providers:
            try:
                messages = [{"role": "user", "content": "Hello"}]
                response = await acompletion(
                    model=provider["model"],
                    messages=messages,
                    max_tokens=10,
                    api_key=provider.get("api_key"),
                    api_base=provider.get("api_base"),
                    api_version=provider.get("api_version"),
                    project_id=provider.get("project_id"),
                )

                response_text = ""
                choices = getattr(response, "choices", None)
                if choices:
                    first_choice = choices[0]
                    message = getattr(first_choice, "message", None)
                    if message is not None:
                        response_text = getattr(message, "content", "") or ""

                results.append({
                    "model": provider["model"],
                    "status": "success",
                    "response": response_text,
                })

            except Exception as e:
                results.append({
                    "model": provider["model"],
                    "status": "failed",
                    "error": str(e),
                })

        return {
            "total_providers": len(self.providers),
            "results": results,
        }

# Made with Bob
