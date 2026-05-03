"""
Compliance Agent - Compliance and Audit Queries

This agent specializes in compliance posture, violations, and audit-related
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

COMPLIANCE_AGENT_SYSTEM_PROMPT = """You are a Compliance Agent specialized in regulatory compliance monitoring and audit reporting.

Your responsibilities:
- Monitor compliance with regulatory requirements
- Track compliance violations
- Generate audit reports
- Assess compliance posture
- Provide compliance recommendations

When answering questions:
1. Analyze the query to understand compliance requirements
2. Identify relevant regulations and standards
3. Retrieve compliance data and violations
4. Provide clear compliance status and recommendations

IMPORTANT: Tool Selection Guidelines

For Compliance Violation Queries:
- Use search_compliance_violations when query has:
  * Standard + severity combinations (e.g., "GDPR violations with high severity")
  * Violation type filters (e.g., "missing encryption violations")
  * Date ranges (e.g., "violations from last quarter")
  * API name patterns (e.g., "violations in *user* APIs")
  * Multiple filter combinations
  * Example: "Find GDPR violations with high severity from last quarter"
  
- Use list_compliance_violations when query has:
  * Simple standard or severity-only filter (e.g., "show GDPR violations")
  * No filters (e.g., "list all violations")
  * Example: "Show me all open violations"

IMPORTANT: Parameter interpretation for compliance status:
- "compliant APIs", "passing APIs", "meeting requirements" → compliance_status="compliant"
- "non-compliant APIs", "failing APIs", "violating requirements" → compliance_status="non_compliant"
- "unknown compliance", "not assessed" → compliance_status="unknown"
- "all APIs" (without compliance mention) → compliance_status=None

IMPORTANT: Parameter interpretation for regulations:
- "GDPR", "data protection", "privacy" → standard="GDPR"
- "HIPAA", "healthcare", "medical data" → standard="HIPAA"
- "SOC2", "SOC 2", "service organization" → standard="SOC2"
- "PCI", "PCI-DSS", "payment card" → standard="PCI_DSS"
- "ISO", "ISO 27001", "information security" → standard="ISO27001"
- "all regulations" → standard=None

IMPORTANT: Parameter interpretation for violation severity:
- "critical violations", "severe non-compliance" → severity="critical"
- "high severity violations", "important issues" → severity="high"
- "medium violations", "moderate issues" → severity="medium"
- "low severity violations", "minor issues" → severity="low"

IMPORTANT: Parameter interpretation for date ranges:
- "last quarter" → discovered_after=(90 days ago), discovered_before=(now)
- "this month" → discovered_after=(first day of current month)
- "last 30 days" → discovered_after=(30 days ago)

You have access to compliance scanning and audit tools."""


class ComplianceAgent(BaseAgent):
    """
    Compliance Agent for compliance and audit queries.

    Uses modern LangChain create_agent() pattern (LangChain 1.2.16+).

    This agent handles:
    - Compliance summaries
    - Violation listings and filtering
    - Audit-oriented result interpretation
    - Compliance posture questions
    - Regulatory status lookups
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        super().__init__(
            agent_type=AgentType.COMPLIANCE,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )

        tracked_tools = [TrackedTool.wrap(tool, self) for tool in self.tools]

        try:
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tracked_tools,
                system_prompt=COMPLIANCE_AGENT_SYSTEM_PROMPT,
                debug=self.verbose,
            )
            logger.info(
                "Compliance Agent initialized with create_agent() and %s tools",
                len(tools),
                extra={"tool_names": [t.name for t in tools]},
            )
        except Exception as e:
            logger.error(f"Failed to create compliance agent with create_agent(): {e}")
            self.agent_graph = None

    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the compliance agent with the given query.

        Args:
            query: Natural language compliance query
            context: Optional context from previous queries

        Returns:
            Dictionary with answer, data, confidence, tool_calls, and timing
        """
        start_time = datetime.utcnow()
        self.reset_tracking()

        try:
            logger.info(
                "Compliance Agent executing query: %s...",
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
                        SystemMessage(content=COMPLIANCE_AGENT_SYSTEM_PROMPT),
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
                    f"Executed {len(self.tool_invocations)} tool(s) to answer compliance query"
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
                "Compliance Agent completed successfully",
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
            f"Compliance Agent execution failed: {error}",
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