"""
Base agent infrastructure for agentic query system.

This module provides the abstract base class for all specialized agents,
including decision logging and tool invocation tracking capabilities.

Feature: 002-agentic-query - Enhanced with LLM-powered synthesis and entity grouping
"""

from abc import ABC, abstractmethod
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from app.models.agent import (
    AgentDecision,
    AgentType,
    EntityGrouping,
    ToolInvocation,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all specialized agents in the agentic query system.
    
    Provides common functionality for:
    - Agent initialization with LLM and tools
    - Decision logging for observability
    - Tool invocation tracking for debugging
    - Agent execution with error handling
    
    Attributes:
        agent_type: Type of agent (Discovery, Metrics, Security, etc.)
        llm: Language model for agent reasoning
        tools: List of tools available to the agent
        agent_executor: LangChain agent executor
        decisions: List of decisions made during execution
        tool_invocations: List of tool invocations during execution
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        llm: BaseChatModel,
        tools: List[BaseTool],
        verbose: bool = False,
        max_iterations: int = 10,
        max_execution_time: Optional[float] = None,
    ):
        """
        Initialize the base agent.
        
        Args:
            agent_type: Type of agent
            llm: Language model for reasoning
            tools: List of tools available to agent
            verbose: Enable verbose logging
            max_iterations: Maximum reasoning iterations
            max_execution_time: Maximum execution time in seconds
        """
        self.agent_type = agent_type
        self.llm = llm
        self.tools = tools
        self.verbose = verbose
        self.max_iterations = max_iterations
        self.max_execution_time = max_execution_time
        
        # Tracking lists
        self.decisions: List[AgentDecision] = []
        self.tool_invocations: List[ToolInvocation] = []
        
        # Agent executor will be initialized by subclasses
        self.agent_executor: Optional[Any] = None
        
        logger.info(
            f"Initialized {agent_type.value} agent with {len(tools)} tools",
            extra={
                "agent_type": agent_type.value,
                "tool_count": len(tools),
                "tool_names": [tool.name for tool in tools],
            }
        )
    
    @abstractmethod
    async def execute(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the agent with the given query and context.
        
        This method must be implemented by subclasses to define
        agent-specific execution logic.
        
        Args:
            query: Natural language query
            context: Optional context from previous queries
            
        Returns:
            Agent execution result
        """
        pass
    
    def log_decision(
        self,
        query_text: str,
        reasoning: str,
        selected_tools: List[str],
        tool_parameters: Dict[str, Dict[str, Any]],
        confidence_score: float,
        execution_time_ms: int,
        context_used: Optional[Dict[str, Any]] = None,
    ) -> AgentDecision:
        """
        Log an agent decision for observability.
        
        Args:
            query_text: The query being processed
            reasoning: Agent's reasoning for the decision
            selected_tools: List of tool names selected
            tool_parameters: Parameters for each tool
            confidence_score: Confidence score (0.0-1.0)
            execution_time_ms: Time taken to make decision
            context_used: Context information used
            
        Returns:
            Logged AgentDecision object
        """
        decision = AgentDecision(
            agent_type=self.agent_type,
            query_text=query_text,
            reasoning=reasoning,
            selected_tools=selected_tools,
            tool_parameters=tool_parameters,
            confidence_score=confidence_score,
            execution_time_ms=execution_time_ms,
            context_used=context_used or {},
        )
        
        self.decisions.append(decision)
        
        logger.debug(
            f"Agent decision logged: {len(selected_tools)} tools selected",
            extra={
                "agent_type": self.agent_type.value,
                "selected_tools": selected_tools,
                "confidence_score": confidence_score,
                "reasoning": reasoning[:100],  # Truncate for logging
            }
        )
        
        return decision
    
    def log_tool_invocation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        execution_time_ms: int,
        success: bool = True,
        error: Optional[str] = None,
        retry_count: int = 0,
    ) -> ToolInvocation:
        """
        Log a tool invocation for debugging and observability.
        
        Args:
            tool_name: Name of the invoked tool
            parameters: Input parameters to the tool
            result: Output from the tool (None if failed)
            execution_time_ms: Execution time in milliseconds
            success: Whether the invocation succeeded
            error: Error message if invocation failed
            retry_count: Number of retries attempted
            
        Returns:
            Logged ToolInvocation object
        """
        invocation = ToolInvocation(
            tool_name=tool_name,
            agent_type=self.agent_type,
            parameters=parameters,
            result=result,
            execution_time_ms=execution_time_ms,
            success=success,
            error=error,
            retry_count=retry_count,
        )
        
        self.tool_invocations.append(invocation)
        
        log_level = "debug" if success else "warning"
        log_message = f"Tool invocation: {tool_name} ({'success' if success else 'failed'})"
        
        getattr(logger, log_level)(
            log_message,
            extra={
                "agent_type": self.agent_type.value,
                "tool_name": tool_name,
                "execution_time_ms": execution_time_ms,
                "success": success,
                "error": error,
            }
        )
        
        return invocation
    
    def reset_tracking(self) -> None:
        """
        Reset decision and tool invocation tracking.
        
        Should be called before each new query execution.
        """
        self.decisions = []
        self.tool_invocations = []
        
        logger.debug(
            f"Reset tracking for {self.agent_type.value} agent",
            extra={"agent_type": self.agent_type.value}
        )
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the agent's execution.
        
        Returns:
            Dictionary containing execution statistics
        """
        total_tool_time = sum(inv.execution_time_ms for inv in self.tool_invocations)
        successful_tools = sum(1 for inv in self.tool_invocations if inv.success)
        failed_tools = len(self.tool_invocations) - successful_tools
        
        return {
            "agent_type": self.agent_type.value,
            "decisions_count": len(self.decisions),
            "tool_invocations_count": len(self.tool_invocations),
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "total_tool_time_ms": total_tool_time,
            "average_confidence": (
                sum(d.confidence_score for d in self.decisions) / len(self.decisions)
                if self.decisions else 0.0
            ),
        }
    
    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute a tool with timing and logging.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            retry_count: Number of retries attempted
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Find the tool
            tool = next((t for t in self.tools if t.name == tool_name), None)
            if not tool:
                raise ValueError(f"Tool not found: {tool_name}")
            
            # Execute the tool
            output = await tool.arun(**parameters)
            
            # Calculate execution time
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Convert output to dict if needed
            result = output if isinstance(output, dict) else {"output": output}
            
            # Log the invocation
            self.log_tool_invocation(
                tool_name=tool_name,
                parameters=parameters,
                result=result,
                execution_time_ms=execution_time_ms,
                success=True,
                retry_count=retry_count,
            )
            
            return result
            
        except Exception as e:
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log the failed invocation
            self.log_tool_invocation(
                tool_name=tool_name,
                parameters=parameters,
                result=None,
                execution_time_ms=execution_time_ms,
                success=False,
                error=str(e),
                retry_count=retry_count,
            )
            
            raise
    
    async def synthesize_results(
        self,
        tool_results: List[Dict[str, Any]],
        query: str,
    ) -> EntityGrouping:
        """
        Use LLM to synthesize and group tool results by entities.
        
        Feature: 002-agentic-query (T047)
        
        This method implements FR-025: Specialized agents MUST use LLM-powered synthesis
        to aggregate and group tool results by entities (e.g., vulnerabilities → APIs)
        before returning to coordinator.
        
        Args:
            tool_results: List of results from tool invocations
            query: Original user query for context
            
        Returns:
            EntityGrouping with synthesized results
        """
        start_time = datetime.utcnow()
        
        try:
            # Extract entities from tool results
            entities = self._extract_entities_from_results(tool_results)
            
            if not entities:
                # No entities found - return empty grouping
                return EntityGrouping(
                    entity_type="unknown",
                    entities={},
                    total_count=0,
                    synthesis_summary="No entities found in tool results",
                    synthesis_reasoning="Tool results contained no identifiable entities",
                    confidence=1.0,
                    source_tool_calls=[inv.tool_name for inv in self.tool_invocations],
                    synthesis_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            # Determine primary entity type
            entity_type = self._determine_primary_entity_type(entities)
            
            # Group entities by ID
            grouped_entities = self._group_entities_by_id(entities, entity_type)
            
            # Use LLM to generate synthesis summary
            synthesis_summary = await self._generate_synthesis_summary(
                query=query,
                entity_type=entity_type,
                entity_count=len(grouped_entities),
                tool_results=tool_results
            )
            
            # Calculate relationships
            related_entities = self._calculate_entity_relationships(entities, entity_type)
            
            synthesis_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            grouping = EntityGrouping(
                entity_type=entity_type,
                entities=grouped_entities,
                total_count=len(grouped_entities),
                synthesis_summary=synthesis_summary,
                synthesis_reasoning=f"Grouped {len(entities)} raw results into {len(grouped_entities)} {entity_type} entities",
                confidence=self._calculate_synthesis_confidence(tool_results),
                related_entities=related_entities,
                source_tool_calls=[inv.tool_name for inv in self.tool_invocations],
                synthesis_time_ms=synthesis_time_ms
            )
            
            logger.info(
                f"Synthesized {len(entities)} results into {len(grouped_entities)} {entity_type} entities",
                extra={
                    "agent_type": self.agent_type.value,
                    "entity_type": entity_type,
                    "entity_count": len(grouped_entities),
                    "synthesis_time_ms": synthesis_time_ms
                }
            )
            
            return grouping
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            # Return minimal grouping on error
            return EntityGrouping(
                entity_type="unknown",
                entities={},
                total_count=0,
                synthesis_summary=f"Synthesis failed: {str(e)}",
                synthesis_reasoning="Error during entity grouping",
                confidence=0.0,
                source_tool_calls=[inv.tool_name for inv in self.tool_invocations],
                synthesis_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
    
    def _extract_entities_from_results(self, tool_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all entities from tool results."""
        entities = []
        
        for result in tool_results:
            if not isinstance(result, dict):
                continue
            
            # Check common list fields
            for list_field in ["apis", "gateways", "vulnerabilities", "predictions",
                              "recommendations", "violations", "metrics"]:
                if list_field in result and isinstance(result[list_field], list):
                    entities.extend(result[list_field])
            
            # Check if result itself is an entity
            if "id" in result:
                entities.append(result)
        
        return entities
    
    def _determine_primary_entity_type(self, entities: List[Dict[str, Any]]) -> str:
        """Determine the primary entity type from entities."""
        # Count entity types
        type_counts: Dict[str, int] = {}
        
        for entity in entities:
            # Try to infer type from fields
            if "api_id" in entity or "api_name" in entity:
                entity_type = "api"
            elif "gateway_id" in entity or "gateway_name" in entity:
                entity_type = "gateway"
            elif "vulnerability_id" in entity or "severity" in entity:
                entity_type = "vulnerability"
            elif "prediction_id" in entity or "likelihood" in entity:
                entity_type = "prediction"
            elif "recommendation_id" in entity or "optimization_type" in entity:
                entity_type = "recommendation"
            elif "violation_id" in entity or "standard" in entity:
                entity_type = "violation"
            else:
                entity_type = "entity"
            
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        # Return most common type
        if type_counts:
            return max(type_counts.items(), key=lambda x: x[1])[0]
        return "entity"
    
    def _group_entities_by_id(
        self,
        entities: List[Dict[str, Any]],
        entity_type: str
    ) -> Dict[str, Dict[str, Any]]:
        """Group entities by their ID."""
        grouped: Dict[str, Dict[str, Any]] = {}
        
        for entity in entities:
            # Get entity ID
            entity_id = (
                entity.get("id") or
                entity.get(f"{entity_type}_id") or
                entity.get("api_id") or
                entity.get("gateway_id") or
                str(hash(json.dumps(entity, sort_keys=True, default=str)))
            )
            
            if entity_id not in grouped:
                grouped[entity_id] = entity
            else:
                # Merge entity data
                grouped[entity_id].update(entity)
        
        return grouped
    
    async def _generate_synthesis_summary(
        self,
        query: str,
        entity_type: str,
        entity_count: int,
        tool_results: List[Dict[str, Any]]
    ) -> str:
        """Use LLM to generate natural language synthesis summary."""
        try:
            # Prepare context for LLM
            context = {
                "query": query,
                "entity_type": entity_type,
                "entity_count": entity_count,
                "tool_results_summary": self._summarize_tool_results(tool_results)
            }
            
            prompt = f"""Synthesize the following query results into a concise natural language summary.

User Query: {query}

Results Summary:
- Entity Type: {entity_type}
- Entity Count: {entity_count}
- Tool Results: {context['tool_results_summary']}

Generate a brief, natural language summary that directly answers the user's query.
Focus on the key findings and entity counts. Be concise (1-2 sentences).

Example: "Found 8 APIs with critical vulnerabilities (40 total vulnerabilities across these APIs)"
"""
            
            messages = [
                SystemMessage(content="You are an expert at synthesizing technical data into clear summaries."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Handle different response types
            if hasattr(response, 'content'):
                summary = response.content
            else:
                summary = str(response)
            
            # Ensure summary is a string
            if isinstance(summary, str):
                return summary.strip()
            else:
                return str(summary).strip()
            
        except Exception as e:
            logger.warning(f"LLM synthesis failed, using fallback: {e}")
            # Fallback to simple summary
            return f"Found {entity_count} {entity_type}(s)"
    
    def _summarize_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Create a brief summary of tool results for LLM context."""
        summaries = []
        
        for result in tool_results[:3]:  # Limit to first 3 results
            if isinstance(result, dict):
                # Count items in lists
                for key, value in result.items():
                    if isinstance(value, list):
                        summaries.append(f"{len(value)} {key}")
        
        return ", ".join(summaries) if summaries else "No data"
    
    def _calculate_entity_relationships(
        self,
        entities: List[Dict[str, Any]],
        primary_entity_type: str
    ) -> Dict[str, List[str]]:
        """Calculate relationships between entities."""
        relationships: Dict[str, List[str]] = {}
        
        for entity in entities:
            # Extract related entity IDs
            for key, value in entity.items():
                if key.endswith("_id") and key != "id" and key != f"{primary_entity_type}_id":
                    entity_type = key.replace("_id", "")
                    if entity_type not in relationships:
                        relationships[entity_type] = []
                    if value and value not in relationships[entity_type]:
                        relationships[entity_type].append(str(value))
        
        return relationships
    
    def _calculate_synthesis_confidence(self, tool_results: List[Dict[str, Any]]) -> float:
        """Calculate confidence in synthesis based on tool results quality."""
        if not tool_results:
            return 0.0
        
        # Base confidence on tool success rate
        if not self.tool_invocations:
            return 0.8
        
        successful = sum(1 for inv in self.tool_invocations if inv.success)
        base_confidence = successful / len(self.tool_invocations)
        
        # Adjust based on result completeness
        complete_results = sum(
            1 for result in tool_results
            if isinstance(result, dict) and result
        )
        completeness_factor = complete_results / len(tool_results) if tool_results else 0.0
        
        return (base_confidence + completeness_factor) / 2


# Made with Bob
