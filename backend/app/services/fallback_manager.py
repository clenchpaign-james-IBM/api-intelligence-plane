"""
Fallback Manager for Agentic Query Service

Manages fallback decision logic to gracefully degrade to OpenSearch query generation
when the agentic workflow cannot determine appropriate tools or encounters errors.

Feature: 001-agentic-query
Phase: 5 (User Story 3)
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
import logging

from app.models.agent import ToolInvocation, FallbackReason

logger = logging.getLogger(__name__)


class FallbackManager:
    """
    Manages fallback decision logic for agentic query service.
    
    Triggers fallback to OpenSearch when:
    1. Confidence score < 0.6 (low confidence)
    2. Tool failure rate > 50% (high failure rate)
    3. Workflow timeout > 10 seconds
    4. No appropriate tools found
    5. LLM service unavailable
    
    Tasks: T061-T066
    """
    
    # Fallback thresholds (configurable) - REALISTIC VALUES for production
    CONFIDENCE_THRESHOLD = 0.6  # Trigger fallback if confidence < 60%
    FAILURE_RATE_THRESHOLD = 0.5  # Trigger fallback if >50% of tools fail
    TIMEOUT_SECONDS = 10.0  # Trigger fallback if workflow takes >10 seconds
    
    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        failure_rate_threshold: float = FAILURE_RATE_THRESHOLD,
        timeout_seconds: float = TIMEOUT_SECONDS,
        opensearch_client: Optional[Any] = None
    ):
        """
        Initialize FallbackManager with configurable thresholds.
        
        Args:
            confidence_threshold: Minimum confidence score (default: 0.6)
            failure_rate_threshold: Maximum tool failure rate (default: 0.5)
            timeout_seconds: Maximum workflow execution time (default: 10.0)
            opensearch_client: Optional OpenSearch client for logging (default: None)
        """
        self.confidence_threshold = confidence_threshold
        self.failure_rate_threshold = failure_rate_threshold
        self.timeout_seconds = timeout_seconds
        self.opensearch_client = opensearch_client
        
        logger.info(
            f"FallbackManager initialized with thresholds: "
            f"confidence={confidence_threshold}, "
            f"failure_rate={failure_rate_threshold}, "
            f"timeout={timeout_seconds}s"
        )
    
    def should_fallback(
        self,
        confidence: float,
        tool_invocations: List[ToolInvocation],
        elapsed_time: float,
        error: Optional[Exception] = None,
        selected_tools: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[FallbackReason], Optional[str]]:
        """
        Determine if fallback should be triggered based on multiple conditions.
        
        Args:
            confidence: Agent confidence score (0.0-1.0)
            tool_invocations: List of tool invocations attempted
            elapsed_time: Time elapsed in workflow (seconds)
            error: Optional exception that occurred
            selected_tools: Optional list of tools selected by agent
        
        Returns:
            Tuple of (should_fallback, fallback_reason, detailed_message)
        
        Tasks: T062-T066
        """
        # T062: Check confidence threshold trigger
        if confidence < self.confidence_threshold:
            message = (
                f"Low confidence score: {confidence:.2f} < {self.confidence_threshold:.2f}. "
                f"Agent is not confident in tool selection."
            )
            logger.warning(f"Fallback triggered: {message}")
            return True, FallbackReason.LOW_CONFIDENCE, message
        
        # T063: Check tool failure rate trigger
        if tool_invocations:
            failures = sum(1 for inv in tool_invocations if not inv.success)
            failure_rate = failures / len(tool_invocations)
            
            if failure_rate > self.failure_rate_threshold:
                message = (
                    f"High tool failure rate: {failure_rate:.1%} "
                    f"({failures}/{len(tool_invocations)} failed) > "
                    f"{self.failure_rate_threshold:.1%}. "
                    f"Too many tool invocations failed."
                )
                logger.warning(f"Fallback triggered: {message}")
                return True, FallbackReason.TOOL_FAILURES, message
        
        # T064: Check workflow timeout trigger
        if elapsed_time > self.timeout_seconds:
            message = (
                f"Workflow timeout: {elapsed_time:.1f}s > {self.timeout_seconds:.1f}s. "
                f"Agentic workflow took too long to complete."
            )
            logger.warning(f"Fallback triggered: {message}")
            return True, FallbackReason.TIMEOUT, message
        
        # T066: Check LLM unavailable trigger
        if error:
            # Check for LLM-related errors
            error_str = str(error).lower()
            llm_error_indicators = [
                'llm', 'openai', 'anthropic', 'model', 'api key',
                'rate limit', 'quota', 'unavailable', 'timeout'
            ]
            
            if any(indicator in error_str for indicator in llm_error_indicators):
                message = (
                    f"LLM service unavailable: {error}. "
                    f"Cannot perform agent reasoning."
                )
                logger.error(f"Fallback triggered: {message}")
                return True, FallbackReason.LLM_UNAVAILABLE, message
        
        # T065: Check no-tools-found trigger
        if selected_tools is not None and len(selected_tools) == 0:
            message = (
                f"No appropriate tools found. "
                f"Agent could not identify tools to answer the query."
            )
            logger.warning(f"Fallback triggered: {message}")
            return True, FallbackReason.NO_TOOLS_FOUND, message
        
        # Also check if no tool invocations occurred (alternative check)
        if not tool_invocations and selected_tools is None:
            message = (
                f"No tool invocations occurred. "
                f"Workflow completed without executing any tools."
            )
            logger.warning(f"Fallback triggered: {message}")
            return True, FallbackReason.NO_TOOLS_FOUND, message
        
        # No fallback needed
        return False, None, None
    
    def check_confidence_trigger(self, confidence: float) -> Tuple[bool, Optional[str]]:
        """
        Check if confidence threshold trigger should activate fallback.
        
        Args:
            confidence: Agent confidence score (0.0-1.0)
        
        Returns:
            Tuple of (should_fallback, message)
        
        Task: T062
        """
        if confidence < self.confidence_threshold:
            message = f"Low confidence: {confidence:.2f} < {self.confidence_threshold:.2f}"
            return True, message
        return False, None
    
    def check_failure_rate_trigger(
        self,
        tool_invocations: List[ToolInvocation]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if tool failure rate trigger should activate fallback.
        
        Args:
            tool_invocations: List of tool invocations attempted
        
        Returns:
            Tuple of (should_fallback, message)
        
        Task: T063
        """
        if not tool_invocations:
            return False, None
        
        failures = sum(1 for inv in tool_invocations if not inv.success)
        failure_rate = failures / len(tool_invocations)
        
        if failure_rate > self.failure_rate_threshold:
            message = (
                f"High failure rate: {failure_rate:.1%} "
                f"({failures}/{len(tool_invocations)} failed)"
            )
            return True, message
        
        return False, None
    
    def check_timeout_trigger(self, elapsed_time: float) -> Tuple[bool, Optional[str]]:
        """
        Check if workflow timeout trigger should activate fallback.
        
        Args:
            elapsed_time: Time elapsed in workflow (seconds)
        
        Returns:
            Tuple of (should_fallback, message)
        
        Task: T064
        """
        if elapsed_time > self.timeout_seconds:
            message = f"Timeout: {elapsed_time:.1f}s > {self.timeout_seconds:.1f}s"
            return True, message
        return False, None
    
    def check_no_tools_trigger(
        self,
        tool_invocations: List[ToolInvocation],
        selected_tools: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if no-tools-found trigger should activate fallback.
        
        Args:
            tool_invocations: List of tool invocations attempted
            selected_tools: Optional list of tools selected by agent
        
        Returns:
            Tuple of (should_fallback, message)
        
        Task: T065
        """
        if selected_tools is not None and len(selected_tools) == 0:
            return True, "No appropriate tools found"
        
        if not tool_invocations and selected_tools is None:
            return True, "No tool invocations occurred"
        
        return False, None
    
    def check_llm_unavailable_trigger(
        self,
        error: Optional[Exception]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if LLM unavailable trigger should activate fallback.
        
        Args:
            error: Optional exception that occurred
        
        Returns:
            Tuple of (should_fallback, message)
        
        Task: T066
        """
        if not error:
            return False, None
        
        error_str = str(error).lower()
        llm_error_indicators = [
            'llm', 'openai', 'anthropic', 'model', 'api key',
            'rate limit', 'quota', 'unavailable', 'timeout'
        ]
        
        if any(indicator in error_str for indicator in llm_error_indicators):
            return True, f"LLM service unavailable: {error}"
        
        return False, None
    
    def get_fallback_statistics(
        self,
        total_queries: int,
        fallback_queries: int
    ) -> dict:
        """
        Calculate fallback statistics for monitoring.
        
        Args:
            total_queries: Total number of queries processed
            fallback_queries: Number of queries that used fallback
        
        Returns:
            Dictionary with fallback statistics
        """
        if total_queries == 0:
            return {
                "total_queries": 0,
                "fallback_queries": 0,
                "fallback_rate": 0.0,
                "agentic_queries": 0,
                "agentic_rate": 0.0
            }
        
        fallback_rate = fallback_queries / total_queries
        agentic_queries = total_queries - fallback_queries
        agentic_rate = agentic_queries / total_queries
        
        return {
            "total_queries": total_queries,
            "fallback_queries": fallback_queries,
            "fallback_rate": fallback_rate,
            "agentic_queries": agentic_queries,
            "agentic_rate": agentic_rate
        }
    
    async def log_fallback_trigger(
        self,
        query_id: UUID,
        query_text: str,
        reason: FallbackReason,
        message: str,
        confidence: float,
        tool_invocations: List[ToolInvocation],
        elapsed_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log fallback trigger to OpenSearch for monitoring and analysis.
        
        Args:
            query_id: Query UUID
            query_text: Original query text
            reason: Fallback reason enum
            message: Detailed fallback message
            confidence: Agent confidence score
            tool_invocations: List of tool invocations attempted
            elapsed_time: Time elapsed in workflow (seconds)
            metadata: Optional additional metadata
        
        Task: T070
        """
        if not self.opensearch_client:
            logger.warning("OpenSearch client not configured, skipping fallback logging")
            return
        
        try:
            # Prepare fallback trigger document
            trigger_doc = {
                "query_id": str(query_id),
                "query_text": query_text,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason.value,
                "message": message,
                "confidence": confidence,
                "elapsed_time_ms": int(elapsed_time * 1000),
                "tool_invocations": [
                    {
                        "tool_name": inv.tool_name,
                        "success": inv.success,
                        "error": inv.error,
                        "execution_time_ms": inv.execution_time_ms,
                    }
                    for inv in tool_invocations
                ],
                "tool_count": len(tool_invocations),
                "failed_tool_count": sum(1 for inv in tool_invocations if not inv.success),
                "failure_rate": (
                    sum(1 for inv in tool_invocations if not inv.success) / len(tool_invocations)
                    if tool_invocations else 0.0
                ),
                "metadata": metadata or {},
            }
            
            # Index to fallback_triggers
            response = self.opensearch_client.index(
                index="fallback_triggers",
                body=trigger_doc,
                refresh=False  # Don't wait for refresh
            )
            
            logger.info(
                f"Logged fallback trigger for query {query_id}: {reason.value}",
                extra={
                    "query_id": str(query_id),
                    "reason": reason.value,
                    "confidence": confidence,
                    "document_id": response.get("_id"),
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to log fallback trigger to OpenSearch: {e}",
                exc_info=True,
                extra={
                    "query_id": str(query_id),
                    "reason": reason.value,
                }
            )

# Made with Bob
