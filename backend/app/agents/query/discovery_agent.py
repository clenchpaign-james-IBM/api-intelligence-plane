"""
Discovery Agent - API Discovery and Gateway Management

This agent specializes in API discovery, gateway management, and API inventory queries.
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
from app.config import settings
from app.models.agent import AgentType
from app.tools.tracked_tool import TrackedTool
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Agent system prompt (simple, no manual template)
DISCOVERY_AGENT_SYSTEM_PROMPT = """You are a Discovery Agent specialized in API discovery and gateway management.

Your responsibilities:
- Answer questions about APIs in the system
- Provide information about API gateways
- Help discover and list APIs
- Retrieve API details and health status
- Manage gateway connections

When answering questions:
1. Analyze the query to understand what API or gateway information is needed
2. Select the appropriate tool(s) to gather the information
3. Use the tools to retrieve accurate data
4. Synthesize the results into a clear, concise answer

IMPORTANT: Tool Selection Guidelines

For Gateway Queries:
- Use search_gateways when query has:
  * Name patterns (e.g., "prod*", "*kong*")
  * Multiple filters (vendor + status, name + created date)
  * Date ranges (created after/before)
  * Example: "Find production Kong gateways that are connected"
  
- Use list_gateways when query has:
  * Simple status-only filter (e.g., "show connected gateways")
  * No filters (e.g., "list all gateways")
  * Example: "Show me all gateways"

For API Queries:
- Use search_apis_global when query has:
  * Name or description patterns (e.g., "payment*", "*user*")
  * Multiple filters (authentication + health score, status + shadow API)
  * Date ranges (created after/before)
  * Health score ranges
  * Example: "Find APIs with 'payment' created last week with authentication enabled"
  
- Use list_all_apis when query has:
  * Simple filters (status only, gateway_id only)
  * No filters (e.g., "list all APIs")
  * Example: "Show me all active APIs"
  
- Use search_apis (gateway-scoped) when query has:
  * Full-text search with fuzzy matching within a specific gateway
  * Example: "Search for 'payment processing' APIs in gateway X"

IMPORTANT: When users ask about gateway status:
- "connected gateways", "active gateways", "online gateways" → Use status="connected"
- "disconnected gateways", "offline gateways", "inactive gateways" → Use status="disconnected"
- "gateways with errors", "failed gateways" → Use status="error"
- "all gateways", "list gateways" (without status mention) → Use status=None

You have access to tools that will be automatically invoked when needed."""


class DiscoveryAgent(BaseAgent):
    """
    Discovery Agent for API discovery and gateway management queries.
    
    Uses modern LangChain create_agent() pattern (LangChain 1.2.16+).
    
    Architecture:
    - BaseAgent: Provides observability infrastructure (log_decision, log_tool_invocation)
    - create_agent(): Provides workflow logic (automatic tool calling, error handling)
    
    This agent handles queries related to:
    - Listing and searching APIs
    - Getting API details and health status
    - Managing API gateways
    - Gateway connection testing
    - API synchronization
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
    ):
        """
        Initialize the Discovery Agent.
        
        Args:
            llm: Language model for reasoning
            tools: List of discovery-related tools
            verbose: Enable verbose logging
        """
        super().__init__(
            agent_type=AgentType.DISCOVERY,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )
        
        # Wrap tools with tracking for accurate observability
        tracked_tools = [TrackedTool.wrap(tool, self) for tool in self.tools]
        
        # Create agent workflow using official LangChain API with recursion limits
        try:
            self.agent_graph = create_agent(
                model=self.llm,
                tools=tracked_tools,  # Use tracked tools
                system_prompt=DISCOVERY_AGENT_SYSTEM_PROMPT,
                debug=self.verbose,
            )
            # Store max iterations for runtime checking
            self.max_iterations = settings.AGENT_MAX_ITERATIONS
            self.max_execution_time = settings.AGENT_MAX_EXECUTION_TIME
            
            logger.info(
                f"Discovery Agent initialized with create_agent() and {len(tools)} tools "
                f"(max_iterations={self.max_iterations}, max_time={self.max_execution_time}s)",
                extra={"tool_names": [t.name for t in tools]}
            )
        except Exception as e:
            logger.error(f"Failed to create agent with create_agent(): {e}")
            self.agent_graph = None
            self.max_iterations = 15  # Fallback default
            self.max_execution_time = 30  # Fallback default
    
    async def execute(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the discovery agent with the given query.
        
        Args:
            query: Natural language query about APIs or gateways
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
                f"Discovery Agent executing query: {query[:100]}...",
                extra={"query_length": len(query)}
            )
            
            # Execute agent workflow with recursion limit
            # Note: Tool invocations are automatically tracked via TrackedTool wrapper
            if self.agent_graph:
                result = await self.agent_graph.ainvoke(
                    {"messages": [HumanMessage(content=query)]},
                    config={"recursion_limit": self.max_iterations}
                )
                messages = result.get("messages", [])
                
                # Check if we hit the recursion limit or execution time
                execution_time_s = (datetime.utcnow() - start_time).total_seconds()
                if len(self.tool_invocations) >= self.max_iterations:
                    logger.warning(
                        f"Discovery Agent hit max iterations limit ({self.max_iterations})",
                        extra={
                            "query": query[:100],
                            "tool_invocations": len(self.tool_invocations)
                        }
                    )
                elif execution_time_s >= self.max_execution_time:
                    logger.warning(
                        f"Discovery Agent exceeded max execution time ({self.max_execution_time}s)",
                        extra={
                            "query": query[:100],
                            "execution_time": execution_time_s
                        }
                    )
            else:
                # Fallback: direct LLM call
                response = await self.llm.ainvoke([
                    SystemMessage(content=DISCOVERY_AGENT_SYSTEM_PROMPT),
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
                reasoning=f"Executed {len(self.tool_invocations)} tool(s) to answer discovery query",
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
                f"Discovery Agent completed successfully",
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
            f"Discovery Agent execution failed: {error}",
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
