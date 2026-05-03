"""
Prediction Agent - Failure Prediction and Forecast Queries

This agent specializes in failure prediction, forecast interpretation, and
risk-oriented predictive analysis queries. Uses modern LangChain
create_agent() pattern for workflow orchestration.

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

PREDICTION_AGENT_SYSTEM_PROMPT = """You are a Prediction Agent specialized in failure prediction and trend forecasting.

Your responsibilities:
- Predict API failures and degradation
- Forecast capacity issues
- Analyze failure trends
- Provide early warning alerts
- Suggest preventive actions

When answering questions:
1. Analyze the query to understand prediction needs
2. Retrieve historical data and patterns
3. Generate predictions with confidence scores
4. Provide actionable preventive recommendations

IMPORTANT: Tool Selection Guidelines

For Prediction Queries:
- Use search_predictions when query has:
  * Confidence ranges (e.g., "predictions with confidence >80%")
  * Prediction type + severity combinations (e.g., "critical failure predictions")
  * Date ranges (e.g., "predictions from last week")
  * API name patterns (e.g., "predictions for *payment* APIs")
  * Multiple filter combinations
  * Example: "Find high-confidence failure predictions with critical severity from last week"
  
- Use list_all_predictions when query has:
  * Simple severity or status-only filter (e.g., "show critical predictions")
  * No filters (e.g., "list all predictions")
  * Example: "Show me all pending predictions"

IMPORTANT: Parameter interpretation for prediction confidence:
- "high confidence predictions", "likely failures", "probable issues" → confidence_min=0.8
- "medium confidence", "possible failures", "potential issues" → confidence_min=0.5, confidence_max=0.8
- "low confidence", "unlikely failures", "low probability" → confidence_max=0.5
- "all predictions" → confidence_min=None, confidence_max=None

IMPORTANT: Parameter interpretation for failure likelihood:
- "likely to fail", "will fail", "expected failures" → confidence_min=0.8
- "might fail", "could fail", "possible failures" → confidence_min=0.5, confidence_max=0.8
- "unlikely to fail", "probably won't fail" → confidence_max=0.5
- "all predictions" → No confidence filter

IMPORTANT: Parameter interpretation for time horizons:
- "next hour", "within an hour", "soon" → predicted_after=(now), predicted_before=(now + 1 hour)
- "next 24 hours", "tomorrow", "next day" → predicted_after=(now), predicted_before=(now + 24 hours)
- "next week", "within a week" → predicted_after=(now), predicted_before=(now + 7 days)
- "last week" → predicted_after=(7 days ago), predicted_before=(now)
- No time mention → Default to next 24 hours

IMPORTANT: Parameter interpretation for prediction types:
- "failure predictions", "outage forecasts" → prediction_type="failure"
- "degradation predictions", "performance decline" → prediction_type="degradation"
- "capacity predictions", "resource exhaustion" → prediction_type="capacity"
- "security predictions", "security incidents" → prediction_type="security"
- "all predictions" → prediction_type=None

You have access to predictive analytics and forecasting tools."""


class PredictionAgent(BaseAgent):
    """
    Prediction Agent for forecast and failure prediction queries.

    Uses modern LangChain create_agent() pattern (LangChain 1.2.16+).

    This agent handles:
    - Failure prediction summaries
    - Predicted incident and degradation lookups
    - Forecast interpretation
    - Risk-oriented API analysis
    - Prediction result summaries and details
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        super().__init__(
            agent_type=AgentType.PREDICTION,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )

        tracked_tools = [TrackedTool.wrap(tool, self) for tool in self.tools]

        try:
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tracked_tools,
                system_prompt=PREDICTION_AGENT_SYSTEM_PROMPT,
                debug=self.verbose,
            )
            logger.info(
                "Prediction Agent initialized with create_agent() and %s tools",
                len(tools),
                extra={"tool_names": [t.name for t in tools]},
            )
        except Exception as e:
            logger.error(f"Failed to create prediction agent with create_agent(): {e}")
            self.agent_graph = None

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the prediction agent with the given query.

        Args:
            query: Natural language prediction query
            context: Optional context from previous queries

        Returns:
            Dictionary with answer, data, confidence, tool_calls, and timing
        """
        start_time = datetime.utcnow()
        self.reset_tracking()

        try:
            logger.info(
                "Prediction Agent executing query: %s...",
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
                        SystemMessage(content=PREDICTION_AGENT_SYSTEM_PROMPT),
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
                    f"Executed {len(self.tool_invocations)} tool(s) to answer prediction query"
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
                "Prediction Agent completed successfully",
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
            f"Prediction Agent execution failed: {error}",
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