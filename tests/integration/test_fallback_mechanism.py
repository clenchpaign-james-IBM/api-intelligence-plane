"""
Integration Tests for Fallback Mechanism (User Story 3)

Tests the intelligent fallback to OpenSearch when agentic workflow
encounters issues or low confidence.

Feature: 002-agentic-query
Tasks: T063-T066
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.services.fallback_manager import FallbackManager
from app.models.agent import ToolInvocation, FallbackReason


@pytest.fixture
def opensearch_client():
    """Mock OpenSearch client."""
    client = MagicMock()
    client.index = MagicMock(return_value={"_id": "test-doc-id", "result": "created"})
    return client


@pytest.fixture
def fallback_manager(opensearch_client):
    """Create FallbackManager with mocked OpenSearch client."""
    return FallbackManager(
        confidence_threshold=0.6,
        failure_rate_threshold=0.5,
        timeout_seconds=10.0,
        opensearch_client=opensearch_client,
    )


class TestLowConfidenceFallback:
    """T063: Test low confidence fallback trigger."""
    
    def test_low_confidence_triggers_fallback(self, fallback_manager):
        """Test that confidence below threshold triggers fallback."""
        # Arrange
        confidence = 0.4  # Below 0.6 threshold
        tool_invocations = []
        elapsed_time = 2.0
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert
        assert should_fallback is True
        assert reason == FallbackReason.LOW_CONFIDENCE
        assert "0.40" in message
        assert "0.60" in message
    
    def test_high_confidence_no_fallback(self, fallback_manager):
        """Test that confidence above threshold does not trigger fallback."""
        # Arrange
        confidence = 0.8  # Above 0.6 threshold
        tool_invocations = []
        elapsed_time = 2.0
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert
        assert should_fallback is False
        assert reason is None
    
    def test_confidence_threshold_boundary(self, fallback_manager):
        """Test confidence exactly at threshold."""
        # Arrange
        confidence = 0.6  # Exactly at threshold
        tool_invocations = []
        elapsed_time = 2.0
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert - should NOT fallback at exactly threshold
        assert should_fallback is False


class TestToolFailureFallback:
    """T064: Test tool failure rate fallback trigger."""
    
    def test_high_failure_rate_triggers_fallback(self, fallback_manager):
        """Test that >50% tool failure rate triggers fallback."""
        # Arrange
        confidence = 0.9
        tool_invocations = [
            ToolInvocation(
                tool_name="tool1",
                success=False,
                error="Tool failed",
                execution_time_ms=100,
            ),
            ToolInvocation(
                tool_name="tool2",
                success=False,
                error="Tool failed",
                execution_time_ms=100,
            ),
            ToolInvocation(
                tool_name="tool3",
                success=True,
                result={"data": "success"},
                execution_time_ms=100,
            ),
        ]  # 2/3 = 66.7% failure rate
        elapsed_time = 2.0
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert
        assert should_fallback is True
        assert reason == FallbackReason.TOOL_FAILURES
        assert "66" in message or "67" in message  # Percentage
        assert "2/3" in message
    
    def test_low_failure_rate_no_fallback(self, fallback_manager):
        """Test that <50% failure rate does not trigger fallback."""
        # Arrange
        confidence = 0.9
        tool_invocations = [
            ToolInvocation(
                tool_name="tool1",
                success=True,
                result={"data": "success"},
                execution_time_ms=100,
            ),
            ToolInvocation(
                tool_name="tool2",
                success=True,
                result={"data": "success"},
                execution_time_ms=100,
            ),
            ToolInvocation(
                tool_name="tool3",
                success=False,
                error="Tool failed",
                execution_time_ms=100,
            ),
        ]  # 1/3 = 33.3% failure rate
        elapsed_time = 2.0
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert
        assert should_fallback is False
    
    def test_failure_rate_threshold_boundary(self, fallback_manager):
        """Test failure rate exactly at 50% threshold."""
        # Arrange
        confidence = 0.9
        tool_invocations = [
            ToolInvocation(tool_name="tool1", success=True, execution_time_ms=100),
            ToolInvocation(tool_name="tool2", success=False, error="Failed", execution_time_ms=100),
        ]  # 1/2 = 50% failure rate
        elapsed_time = 2.0
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert - should NOT fallback at exactly threshold
        assert should_fallback is False


class TestTimeoutFallback:
    """T065: Test timeout fallback trigger."""
    
    def test_timeout_triggers_fallback(self, fallback_manager):
        """Test that elapsed time > 10s triggers fallback."""
        # Arrange
        confidence = 0.9
        tool_invocations = []
        elapsed_time = 12.0  # Above 10s threshold
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert
        assert should_fallback is True
        assert reason == FallbackReason.TIMEOUT
        assert "12.0" in message
        assert "10.0" in message
    
    def test_no_timeout_no_fallback(self, fallback_manager):
        """Test that elapsed time < 10s does not trigger fallback."""
        # Arrange
        confidence = 0.9
        tool_invocations = []
        elapsed_time = 5.0  # Below 10s threshold
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert
        assert should_fallback is False
    
    def test_timeout_threshold_boundary(self, fallback_manager):
        """Test timeout exactly at 10s threshold."""
        # Arrange
        confidence = 0.9
        tool_invocations = []
        elapsed_time = 10.0  # Exactly at threshold
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert - should NOT fallback at exactly threshold
        assert should_fallback is False


class TestFallbackTriggerLogging:
    """T066: Test fallback trigger logging to OpenSearch."""
    
    @pytest.mark.asyncio
    async def test_log_fallback_trigger_success(self, fallback_manager, opensearch_client):
        """Test successful logging of fallback trigger."""
        # Arrange
        query_id = uuid4()
        query_text = "Test query"
        reason = FallbackReason.LOW_CONFIDENCE
        message = "Low confidence score"
        confidence = 0.4
        tool_invocations = [
            ToolInvocation(
                tool_name="test_tool",
                success=False,
                error="Tool failed",
                execution_time_ms=100,
            )
        ]
        elapsed_time = 2.5
        metadata = {"test": "metadata"}
        
        # Act
        await fallback_manager.log_fallback_trigger(
            query_id=query_id,
            query_text=query_text,
            reason=reason,
            message=message,
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
            metadata=metadata,
        )
        
        # Assert
        opensearch_client.index.assert_called_once()
        call_args = opensearch_client.index.call_args
        
        # Verify index name
        assert call_args[1]["index"] == "fallback_triggers"
        
        # Verify document structure
        doc = call_args[1]["body"]
        assert doc["query_id"] == str(query_id)
        assert doc["query_text"] == query_text
        assert doc["reason"] == reason.value
        assert doc["message"] == message
        assert doc["confidence"] == confidence
        assert doc["elapsed_time_ms"] == 2500
        assert doc["tool_count"] == 1
        assert doc["failed_tool_count"] == 1
        assert doc["failure_rate"] == 1.0
        assert "timestamp" in doc
        assert doc["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_log_fallback_trigger_without_opensearch(self):
        """Test logging when OpenSearch client is not configured."""
        # Arrange
        fallback_manager = FallbackManager(
            opensearch_client=None  # No OpenSearch client
        )
        
        # Act - should not raise exception
        await fallback_manager.log_fallback_trigger(
            query_id=uuid4(),
            query_text="Test query",
            reason=FallbackReason.LOW_CONFIDENCE,
            message="Test message",
            confidence=0.4,
            tool_invocations=[],
            elapsed_time=2.0,
        )
        
        # Assert - no exception raised
    
    @pytest.mark.asyncio
    async def test_log_fallback_trigger_handles_opensearch_error(
        self, fallback_manager, opensearch_client
    ):
        """Test that logging handles OpenSearch errors gracefully."""
        # Arrange
        opensearch_client.index.side_effect = Exception("OpenSearch error")
        
        # Act - should not raise exception
        await fallback_manager.log_fallback_trigger(
            query_id=uuid4(),
            query_text="Test query",
            reason=FallbackReason.TIMEOUT,
            message="Timeout occurred",
            confidence=0.9,
            tool_invocations=[],
            elapsed_time=12.0,
        )
        
        # Assert - no exception raised, error logged


class TestMultipleFallbackTriggers:
    """Test scenarios with multiple fallback triggers."""
    
    def test_first_trigger_wins(self, fallback_manager):
        """Test that first triggered condition is returned."""
        # Arrange - both low confidence AND timeout
        confidence = 0.3  # Triggers LOW_CONFIDENCE
        tool_invocations = []
        elapsed_time = 15.0  # Also triggers TIMEOUT
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
        )
        
        # Assert - LOW_CONFIDENCE checked first
        assert should_fallback is True
        assert reason == FallbackReason.LOW_CONFIDENCE
    
    def test_no_tools_found_trigger(self, fallback_manager):
        """Test NO_TOOLS_FOUND trigger."""
        # Arrange
        confidence = 0.9
        tool_invocations = []
        elapsed_time = 2.0
        selected_tools = []  # No tools selected
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
            selected_tools=selected_tools,
        )
        
        # Assert
        assert should_fallback is True
        assert reason == FallbackReason.NO_TOOLS_FOUND
    
    def test_llm_unavailable_trigger(self, fallback_manager):
        """Test LLM_UNAVAILABLE trigger."""
        # Arrange
        confidence = 0.9
        tool_invocations = []
        elapsed_time = 2.0
        error = Exception("OpenAI API key invalid")
        
        # Act
        should_fallback, reason, message = fallback_manager.should_fallback(
            confidence=confidence,
            tool_invocations=tool_invocations,
            elapsed_time=elapsed_time,
            error=error,
        )
        
        # Assert
        assert should_fallback is True
        assert reason == FallbackReason.LLM_UNAVAILABLE


# Made with Bob