"""
Metrics Agent - Performance and Analytics Queries

This agent specializes in performance metrics, analytics, and API usage queries.
Uses modern LangChain create_agent() pattern for workflow orchestration.

Feature: 001-agentic-query
Architecture Reference: docs/agentic-query-architecture-design.md Section 3.3
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.agents.query.base_agent import BaseAgent
from app.models.agent import AgentType
from app.tools.tracked_tool import TrackedTool
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Agent system prompt with enhanced parameter interpretation guidance
METRICS_AGENT_SYSTEM_PROMPT = """You are a Metrics Agent specialized in performance monitoring and analytics.

Your responsibilities:
- Monitor API performance metrics (latency, throughput, error rates)
- Analyze traffic patterns and trends
- Identify performance bottlenecks
- Track SLA compliance
- Provide performance insights

When answering questions:
1. Analyze the query to understand what metrics are needed
2. Determine appropriate time ranges and filters
3. Retrieve and aggregate metrics data
4. Provide clear performance insights

IMPORTANT: Parameter interpretation for performance:
- "slow APIs", "high latency APIs", "performance issues" → latency_threshold > 500ms
- "fast APIs", "low latency APIs", "good performance" → latency_threshold < 100ms
- "APIs with errors", "failing APIs", "error-prone APIs" → error_rate > 0.01 (1%)
- "high traffic APIs", "busy APIs", "popular APIs" → Sort by request_count DESC

IMPORTANT: Parameter interpretation for time ranges:
- "last hour", "past hour", "recent" → time_range: now-1h to now
- "last 24 hours", "today", "past day" → time_range: now-24h to now
- "last week", "past week", "past 7 days" → time_range: now-7d to now
- "last month", "past month", "past 30 days" → time_range: now-30d to now
- No time mention → Default to last 24 hours

IMPORTANT: Parameter interpretation for comparisons:
- "greater than X", "more than X", "above X", "over X" → Use gt=X or gte=X
- "less than X", "fewer than X", "below X", "under X" → Use lt=X or lte=X
- "at least X", "minimum X" → Use gte=X
- "at most X", "maximum X" → Use lte=X

You have access to metrics collection and analysis tools."""


class MetricsAgent(BaseAgent):
    """
    Metrics Agent for performance and analytics queries.
    
    Uses modern LangChain create_agent() pattern (LangChain 1.2.16+).
    
    Architecture:
    - BaseAgent: Provides observability infrastructure (log_decision, log_tool_invocation)
    - create_agent(): Provides workflow logic (automatic tool calling, error handling)
    
    This agent handles queries related to:
    - API performance metrics (response time, throughput, error rates)
    - Usage analytics and patterns
    - Performance trends and anomalies
    - Comparative analysis across APIs
    - Time-series metrics queries
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        """
        Initialize the Metrics Agent.
        
        Args:
            llm: Language model for reasoning
            tools: List of metrics-related tools
            verbose: Enable verbose logging
        """
        super().__init__(
            agent_type=AgentType.METRICS,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )
        
        # Wrap tools with tracking for accurate observability
        tracked_tools = [TrackedTool.wrap(tool, self) for tool in self.tools]
        
        # Create agent workflow using official LangChain API
        try:
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tracked_tools,  # Use tracked tools
                system_prompt=METRICS_AGENT_SYSTEM_PROMPT,
                debug=self.verbose,
            )
            logger.info(
                f"Metrics Agent initialized with create_agent() and {len(tools)} tools",
                extra={"tool_names": [t.name for t in tools]}
            )
        except Exception as e:
            logger.error(f"Failed to create agent with create_agent(): {e}")
            self.agent_graph = None
    
    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the metrics agent with the given query.
        
        Args:
            query: Natural language query about metrics or analytics
            context: Optional context from previous queries
            
        Returns:
            Dictionary containing:
                - answer: Natural language response
                - data: Structured data from tool invocations
                - confidence: Confidence score (0.0-1.0)
                - tool_calls: List of tools invoked
        """
        start_time = datetime.utcnow()
        
        # Reset tracking for new query
        self.reset_tracking()
        
        try:
            logger.info(
                f"Metrics Agent executing query: {query[:100]}...",
                extra={"query_length": len(query)}
            )
            
            # Execute agent workflow
            # Note: Tool invocations are automatically tracked via TrackedTool wrapper
            if self.agent_graph:
                result = await self.agent_graph.ainvoke({
                    "messages": [HumanMessage(content=query)]
                })
                messages = result.get("messages", [])
            else:
                # Fallback: direct LLM call
                response = await self.llm.ainvoke([
                    SystemMessage(content=METRICS_AGENT_SYSTEM_PROMPT),
                    HumanMessage(content=query)
                ])
                messages = [response]
            
            # Calculate execution time
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Calculate confidence based on tool success rate
            confidence = self._calculate_confidence()
            
            # Log the decision
            self.log_decision(
                query_text=query,
                reasoning=f"Executed {len(self.tool_invocations)} tool(s) to answer metrics query",
                selected_tools=[inv.tool_name for inv in self.tool_invocations],
                tool_parameters={
                    inv.tool_name: inv.parameters 
                    for inv in self.tool_invocations
                },
                confidence_score=confidence,
                execution_time_ms=execution_time_ms,
                context_used=context or {}
            )
            
            # Extract final answer from messages
            if messages:
                final_message = messages[-1]
                answer = final_message.content if hasattr(final_message, 'content') else str(final_message)
            else:
                answer = "No response generated"
            
            # Prepare response
            response = {
                "answer": answer,
                "data": {
                    "tool_results": [
                        {
                            "tool": inv.tool_name,
                            "result": inv.result,
                            "success": inv.success
                        }
                        for inv in self.tool_invocations
                    ]
                },
                "confidence": confidence,
                "tool_calls": [inv.tool_name for inv in self.tool_invocations],
                "execution_time_ms": execution_time_ms
            }
            
            logger.info(
                f"Metrics Agent completed successfully",
                extra={
                    "execution_time_ms": execution_time_ms,
                    "tool_count": len(self.tool_invocations),
                    "confidence": confidence
                }
            )
            
            return response
            
        except Exception as e:
            return self._error_response(e, start_time, query)
    
    def _calculate_confidence(self) -> float:
        """Calculate confidence based on tool success rate."""
        if not self.tool_invocations:
            return 0.8  # Default confidence when no tools used
        successful = sum(1 for inv in self.tool_invocations if inv.success)
        return successful / len(self.tool_invocations)
    
    def _error_response(self, error: Exception, start_time: datetime, query: str) -> Dict[str, Any]:
        """Generate error response."""
        execution_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )
        
        logger.error(
            f"Metrics Agent execution failed: {error}",
            exc_info=True,
            extra={
                "query": query[:100],
                "execution_time_ms": execution_time_ms
            }
        )
        
        return {
            "answer": f"I encountered an error while processing your query: {str(error)}",
            "data": {},
            "confidence": 0.0,
            "tool_calls": [],
            "execution_time_ms": execution_time_ms,
            "error": str(error)
        }

# Made with Bob
