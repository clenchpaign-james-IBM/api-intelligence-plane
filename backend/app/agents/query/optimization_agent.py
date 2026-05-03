"""
Optimization Agent - Optimization and Rate Limiting Queries

This agent specializes in optimization recommendations, performance tuning,
and rate limiting related queries. Uses modern LangChain create_agent() pattern
for workflow orchestration.

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

OPTIMIZATION_AGENT_SYSTEM_PROMPT = """You are an Optimization Agent specialized in performance optimization and efficiency improvements.

Your responsibilities:
- Generate optimization recommendations
- Analyze rate limiting and throttling policies
- Identify caching opportunities
- Suggest compression strategies
- Track optimization implementation status

When answering questions:
1. Analyze the query to understand optimization needs
2. Identify performance bottlenecks
3. Generate actionable recommendations
4. Track recommendation implementation

IMPORTANT: Tool Selection Guidelines

For Recommendation Queries:
- Use search_recommendations when query has:
  * Type + priority combinations (e.g., "high priority caching recommendations")
  * Impact ranges (e.g., "recommendations with >20% impact")
  * Status + type combinations (e.g., "pending rate limiting recommendations")
  * API name patterns (e.g., "recommendations for *checkout* APIs")
  * Date ranges (e.g., "recommendations from last month")
  * Example: "Find high-priority caching recommendations with >20% impact that are pending"
  
- Use list_recommendations when query has:
  * Simple status or priority-only filter (e.g., "show pending recommendations")
  * No filters (e.g., "list all recommendations")
  * Example: "Show me all high-priority recommendations"

IMPORTANT: Parameter interpretation for recommendation status:
- "pending recommendations", "new suggestions", "not applied" → status="pending"
- "in progress", "being implemented" → status="in_progress"
- "implemented recommendations", "applied suggestions", "active" → status="implemented"
- "rejected recommendations", "declined suggestions" → status="rejected"
- "all recommendations" → status=None

IMPORTANT: Parameter interpretation for optimization types:
- "caching recommendations", "cache suggestions" → type="caching"
- "rate limiting", "throttling", "request limits" → type="rate_limiting"
- "compression", "payload optimization" → type="compression"
- "connection pooling", "connection optimization" → type="connection_pooling"
- "all optimizations" → type=None

IMPORTANT: Parameter interpretation for priority:
- "high priority", "urgent", "critical optimizations" → priority="high"
- "medium priority", "important" → priority="medium"
- "low priority", "nice to have" → priority="low"
- "all priorities" → priority=None

IMPORTANT: Parameter interpretation for impact:
- "high impact", "significant improvements" → impact_min=20
- "medium impact", "moderate improvements" → impact_min=10, impact_max=20
- "low impact", "minor improvements" → impact_max=10

You have access to optimization analysis and recommendation tools."""


class OptimizationAgent(BaseAgent):
    """
    Optimization Agent for optimization and rate limiting queries.

    Uses modern LangChain create_agent() pattern (LangChain 1.2.16+).

    This agent handles:
    - Optimization recommendations
    - Rate limiting analysis
    - API efficiency and tuning questions
    - Performance improvement opportunities
    - Recommendation summaries and details
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        super().__init__(
            agent_type=AgentType.OPTIMIZATION,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )

        tracked_tools = [TrackedTool.wrap(tool, self) for tool in self.tools]

        try:
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tracked_tools,
                system_prompt=OPTIMIZATION_AGENT_SYSTEM_PROMPT,
                debug=self.verbose,
            )
            logger.info(
                "Optimization Agent initialized with create_agent() and %s tools",
                len(tools),
                extra={"tool_names": [t.name for t in tools]},
            )
        except Exception as e:
            logger.error(f"Failed to create optimization agent with create_agent(): {e}")
            self.agent_graph = None

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the optimization agent with the given query.

        Args:
            query: Natural language optimization query
            context: Optional context from previous queries

        Returns:
            Dictionary with answer, data, confidence, tool_calls, and timing
        """
        start_time = datetime.utcnow()
        self.reset_tracking()

        try:
            logger.info(
                "Optimization Agent executing query: %s...",
                query[:100],
                extra={"query_length": len(query)},
            )

            if self.agent_graph:
                result = await self.agent_graph.ainvoke(
                    {"messages": [HumanMessage(content=query)]}
                )
                messages = result.get("messages", [])
            else:
                response = await self.llm.ainvoke(
                    [
                        SystemMessage(content=OPTIMIZATION_AGENT_SYSTEM_PROMPT),
                        HumanMessage(content=query),
                    ]
                )
                messages = [response]

            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            confidence = self._calculate_confidence()

            self.log_decision(
                query_text=query,
                reasoning=(
                    f"Executed {len(self.tool_invocations)} tool(s) to answer optimization query"
                ),
                selected_tools=[inv.tool_name for inv in self.tool_invocations],
                tool_parameters={
                    inv.tool_name: inv.parameters for inv in self.tool_invocations
                },
                confidence_score=confidence,
                execution_time_ms=execution_time_ms,
                context_used=context or {},
            )

            if messages:
                final_message = messages[-1]
                answer = (
                    final_message.content
                    if hasattr(final_message, "content")
                    else str(final_message)
                )
            else:
                answer = "No response generated"

            response = {
                "answer": answer,
                "data": {
                    "tool_results": [
                        {
                            "tool": inv.tool_name,
                            "result": inv.result,
                            "success": inv.success,
                        }
                        for inv in self.tool_invocations
                    ]
                },
                "confidence": confidence,
                "tool_calls": [inv.tool_name for inv in self.tool_invocations],
                "execution_time_ms": execution_time_ms,
            }

            logger.info(
                "Optimization Agent completed successfully",
                extra={
                    "execution_time_ms": execution_time_ms,
                    "tool_count": len(self.tool_invocations),
                    "confidence": confidence,
                },
            )
            return response

        except Exception as e:
            return self._error_response(e, start_time, query)

    def _calculate_confidence(self) -> float:
        """Calculate confidence based on tool success rate."""
        if not self.tool_invocations:
            return 0.8
        successful = sum(1 for inv in self.tool_invocations if inv.success)
        return successful / len(self.tool_invocations)

    def _error_response(
        self, error: Exception, start_time: datetime, query: str
    ) -> Dict[str, Any]:
        """Generate error response."""
        execution_time_ms = int(
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        logger.error(
            f"Optimization Agent execution failed: {error}",
            exc_info=True,
            extra={
                "query": query[:100],
                "execution_time_ms": execution_time_ms,
            },
        )

        return {
            "answer": f"I encountered an error while processing your query: {str(error)}",
            "data": {},
            "confidence": 0.0,
            "tool_calls": [],
            "execution_time_ms": execution_time_ms,
            "error": str(error),
        }

# Made with Bob