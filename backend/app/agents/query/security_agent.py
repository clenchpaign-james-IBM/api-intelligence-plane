"""
Security Agent - Security and Vulnerability Queries

This agent specializes in security posture, vulnerabilities, and remediation
queries. Uses modern LangChain create_agent() pattern for workflow orchestration.

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

SECURITY_AGENT_SYSTEM_PROMPT = """You are a Security Agent specialized in vulnerability management and security posture analysis.

Your responsibilities:
- Identify and report security vulnerabilities
- Analyze security posture across APIs and gateways
- Track vulnerability remediation status
- Provide security recommendations
- Monitor security findings and threats

When answering questions:
1. Analyze the query to understand what security information is needed
2. Select the appropriate security tools
3. Retrieve and analyze security data
4. Provide actionable security insights

IMPORTANT: Tool Selection Guidelines

For Vulnerability Queries:
- Use search_vulnerabilities when query has:
  * Severity + date range combinations (e.g., "critical vulnerabilities this month")
  * API name patterns (e.g., "vulnerabilities in *payment* APIs")
  * Vulnerability type filters (e.g., "SQL injection vulnerabilities")
  * Multiple filter combinations (severity + status + date)
  * Example: "Find critical open vulnerabilities discovered in the last week"
  
- Use list_all_vulnerabilities when query has:
  * Simple severity or status-only filter (e.g., "show critical vulnerabilities")
  * No filters (e.g., "list all vulnerabilities")
  * Example: "Show me all open vulnerabilities"

IMPORTANT: Parameter interpretation for severity:
- "critical vulnerabilities", "severe issues", "urgent security problems" → severity="critical"
- "high severity", "important vulnerabilities", "serious issues" → severity="high"
- "medium severity", "moderate vulnerabilities" → severity="medium"
- "low severity", "minor vulnerabilities", "informational" → severity="low"
- "all vulnerabilities" (without severity mention) → severity=None

IMPORTANT: Parameter interpretation for status:
- "open vulnerabilities", "unresolved issues", "active threats" → status="open"
- "in progress", "being fixed", "under remediation" → status="in_progress"
- "resolved vulnerabilities", "fixed issues", "closed" → status="resolved"
- "all vulnerabilities" (without status mention) → status=None

IMPORTANT: Parameter interpretation for date ranges:
- "this month" → discovered_after=(first day of current month)
- "last week" → discovered_after=(7 days ago), discovered_before=(now)
- "last 30 days" → discovered_after=(30 days ago)

IMPORTANT: Parameter interpretation for affected entities:
- "API vulnerabilities", "API security issues" → Filter by api_id or use api_name pattern
- "gateway vulnerabilities", "gateway security issues" → Filter by gateway_id
- "all security issues" → No entity filter

You have access to security scanning and analysis tools."""


class SecurityAgent(BaseAgent):
    """
    Security Agent for vulnerability and security posture queries.

    Uses modern LangChain create_agent() pattern (LangChain 1.2.16+).

    This agent handles:
    - Security summaries
    - Vulnerability listings and filters
    - Security posture analysis
    - API security scan results
    - Vulnerability remediation lookups
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        super().__init__(
            agent_type=AgentType.SECURITY,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )

        tracked_tools = [TrackedTool.wrap(tool, self) for tool in self.tools]

        try:
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tracked_tools,
                system_prompt=SECURITY_AGENT_SYSTEM_PROMPT,
                debug=self.verbose,
            )
            logger.info(
                "Security Agent initialized with create_agent() and %s tools",
                len(tools),
                extra={"tool_names": [t.name for t in tools]},
            )
        except Exception as e:
            logger.error(f"Failed to create security agent with create_agent(): {e}")
            self.agent_graph = None

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the security agent with the given query.

        Args:
            query: Natural language security query
            context: Optional context from previous queries

        Returns:
            Dictionary with answer, data, confidence, tool_calls, and timing
        """
        start_time = datetime.utcnow()
        self.reset_tracking()

        try:
            logger.info(
                "Security Agent executing query: %s...",
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
                        SystemMessage(content=SECURITY_AGENT_SYSTEM_PROMPT),
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
                    f"Executed {len(self.tool_invocations)} tool(s) to answer security query"
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
                "Security Agent completed successfully",
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
            f"Security Agent execution failed: {error}",
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