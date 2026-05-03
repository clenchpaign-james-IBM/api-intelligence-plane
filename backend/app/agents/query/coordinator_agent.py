"""
Coordinator Agent - Fully Agentic Query Analysis and Agent Selection

Coordinates both single-agent and multi-agent agentic query execution using LLM reasoning
to select the most relevant specialized agents and synthesize results.

**FULLY AGENTIC**: Uses LLM for ALL decisions - no keyword matching!

Feature: 001-agentic-query
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.agents.query.base_agent import BaseAgent
from app.models.agent import AgentType, CoordinatorState
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Pydantic models for structured LLM outputs
class AgentSelectionDecision(BaseModel):
    """LLM decision for single-agent selection."""
    selected_agent: str = Field(description="The agent type to handle this query (discovery, metrics, security, compliance, optimization, prediction)")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Explanation of why this agent was selected")


class MultiAgentDecomposition(BaseModel):
    """LLM decision for multi-agent decomposition."""
    is_multi_agent: bool = Field(description="Whether multiple agents are needed")
    required_agents: List[str] = Field(description="List of agent types needed (discovery, metrics, security, compliance, optimization, prediction)")
    execution_strategy: str = Field(description="Either 'parallel' or 'sequential'")
    reasoning: str = Field(description="Explanation of the decomposition decision")
    sub_queries: Dict[str, str] = Field(description="Map of agent type to specific sub-query for that agent")


class CompletionDecision(BaseModel):
    """
    LLM decision for query completion evaluation.
    
    Feature: 002-agentic-query (Iterative Multi-Step Coordinator Reasoning)
    """
    is_complete: bool = Field(description="Whether the query is fully answered")
    confidence: float = Field(description="Confidence in completion decision (0.0-1.0)")
    reasoning: str = Field(description="Explanation of why query is/isn't complete")
    next_action: Optional[str] = Field(default=None, description="Suggested next action if not complete")


class CoordinatorAgent:
    """
    Fully Agentic Coordinator for query execution.

    **KEY CHANGE**: Uses LLM reasoning for ALL decisions instead of keyword matching!

    Responsibilities:
    - Use LLM to analyze user query intent
    - Use LLM to select the most appropriate specialized agent(s)
    - Use LLM to decompose complex queries for multi-agent collaboration
    - Execute single-agent or multi-agent workflows
    - Synthesize results from multiple agents
    """

    # System prompts for LLM-based decision making
    AGENT_SELECTION_PROMPT = """You are an intelligent coordinator that analyzes user queries and selects the most appropriate specialized agent.

Available agents and their capabilities:

1. **discovery**: Handles queries about APIs, gateways, API inventory, API discovery, listing APIs, searching APIs, gateway management, API health status
2. **metrics**: Handles queries about performance, latency, response times, throughput, traffic, analytics, error rates, slow APIs, API performance
3. **security**: Handles queries about vulnerabilities, security posture, threats, CVEs, security scans, security findings, remediation, security risks
4. **compliance**: Handles queries about compliance violations, regulatory requirements, audits, GDPR, HIPAA, SOC2, PCI, ISO standards
5. **optimization**: Handles queries about optimization recommendations, rate limiting, throttling, caching, compression, efficiency improvements
6. **prediction**: Handles queries about failure predictions, forecasts, future trends, likely failures, degradation predictions

Analyze the user's query and select the SINGLE MOST APPROPRIATE agent that can best answer it.

Return your decision as JSON with:
- selected_agent: The agent type (discovery, metrics, security, compliance, optimization, prediction)
- confidence: Your confidence score (0.0 to 1.0)
- reasoning: Brief explanation of your choice

User Query: {query}

Context from previous queries: {context}"""

    MULTI_AGENT_DECOMPOSITION_PROMPT = """You are an intelligent coordinator that determines if a query requires multiple specialized agents working together.

Available agents:
- discovery: APIs, gateways, inventory
- metrics: Performance, latency, throughput
- security: Vulnerabilities, threats, security posture
- compliance: Regulatory compliance, violations, audits
- optimization: Recommendations, rate limiting, caching, compression, efficiency
- prediction: Failure forecasts, degradation predictions

Analyze the query and determine:
1. Does it require multiple agents? (e.g., "APIs with high latency AND security vulnerabilities" needs metrics + security)
2. Which agents are needed?
3. Should they run in parallel or sequential? (sequential if one depends on another's results)
4. What specific sub-query should each agent handle?

Return JSON with:
- is_multi_agent: true/false
- required_agents: List of agent types needed
- execution_strategy: "parallel" or "sequential"
- reasoning: Explanation of your decision
- sub_queries: Map of agent_type to specific sub-query for that agent

User Query: {query}

Context: {context}"""

    COMPLETION_EVALUATION_PROMPT = """You are an intelligent coordinator evaluating whether a user's query has been fully answered.

Original Query: {query}

Completed Steps So Far:
{completed_steps}

Latest Results:
{latest_results}

Intermediate Results from Previous Steps:
{intermediate_results}

Evaluate whether the query is FULLY answered:
1. Does the latest result directly answer the user's question?
2. Is any additional information needed?
3. Are there any unresolved dependencies or missing data?
4. Would invoking another agent provide valuable additional context?

Return JSON with:
- is_complete: true/false (true ONLY if query is fully answered)
- confidence: Your confidence score (0.0 to 1.0)
- reasoning: Explanation of your decision
- next_action: If not complete, what should be done next? (optional)

Be conservative: Only mark as complete if you're confident the query is fully answered."""

    def __init__(
        self,
        llm: BaseChatModel,
        agents: Dict[AgentType, BaseAgent],
        verbose: bool = False,
    ) -> None:
        self.llm = llm
        self.agents = agents
        self.verbose = verbose
        
        # JSON output parsers for structured LLM responses
        self.agent_selection_parser = JsonOutputParser(pydantic_object=AgentSelectionDecision)
        self.decomposition_parser = JsonOutputParser(pydantic_object=MultiAgentDecomposition)
        self.completion_parser = JsonOutputParser(pydantic_object=CompletionDecision)

    async def analyze_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze query and select the most relevant agent.
        
        **FULLY AGENTIC**: No keyword matching - pure LLM reasoning!
        """
        start_time = datetime.utcnow()
        
        try:
            # Prepare context summary for LLM
            context_summary = self._prepare_context_summary(context)
            
            # Ask LLM to select agent
            prompt = self.AGENT_SELECTION_PROMPT.format(
                query=query,
                context=context_summary
            )
            
            messages = [
                SystemMessage(content="You are an expert at analyzing queries and selecting the right agent."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse LLM response
            content = ""
            try:
                # Handle response content which can be str or list
                content = response.content if isinstance(response.content, str) else str(response.content)
                
                # Strip markdown code blocks if present
                content = self._strip_markdown_code_blocks(content)
                
                decision_dict = self.agent_selection_parser.parse(content)
                decision = AgentSelectionDecision(**decision_dict)
            except Exception as e:
                logger.warning(f"Failed to parse LLM response, using fallback: {e}, content: {content[:200]}")
                # Fallback to discovery agent if parsing fails
                decision = AgentSelectionDecision(
                    selected_agent="discovery",
                    confidence=0.5,
                    reasoning="Failed to parse LLM response, defaulting to discovery agent"
                )
            
            # Convert agent string to AgentType enum
            try:
                agent_type = AgentType(decision.selected_agent)
            except ValueError:
                logger.warning(f"Invalid agent type '{decision.selected_agent}', defaulting to discovery")
                agent_type = AgentType.DISCOVERY
                decision.confidence = 0.5
            
            # Verify agent exists
            if agent_type not in self.agents:
                logger.warning(f"Selected agent {agent_type.value} not registered, falling back to discovery")
                agent_type = AgentType.DISCOVERY
                decision.confidence = 0.5
            
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.info(
                f"LLM selected {agent_type.value} agent with confidence {decision.confidence:.2f}",
                extra={
                    "agent_type": agent_type.value,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                }
            )
            
            return {
                "agent_type": agent_type,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
                "execution_time_ms": execution_time_ms,
                "context": context or {},
            }
            
        except Exception as e:
            logger.error(f"LLM agent selection failed: {e}", exc_info=True)
            # Fallback to discovery agent on error
            return {
                "agent_type": AgentType.DISCOVERY,
                "confidence": 0.3,
                "reasoning": f"LLM selection failed: {str(e)}, defaulting to discovery agent",
                "execution_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "context": context or {},
            }

    async def execute_single_agent_workflow(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single-agent workflow using LLM-selected agent.
        """
        analysis = await self.analyze_query(query=query, context=context)
        agent_type: AgentType = analysis["agent_type"]
        agent = self.agents[agent_type]

        logger.info(
            f"Executing single-agent workflow with {agent_type.value}",
            extra={
                "agent_type": agent_type.value,
                "confidence": analysis["confidence"],
            },
        )

        agent_result = await agent.execute(query=query, context=context)
        return self.synthesize_result(
            query=query,
            agent_type=agent_type,
            agent_result=agent_result,
            analysis=analysis,
        )

    def synthesize_result(
        self,
        query: str,
        agent_type: AgentType,
        agent_result: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Produce a normalized coordinator response from a specialized agent result.
        """
        return {
            "query_text": query,
            "selected_agent": agent_type,
            "reasoning": analysis["reasoning"],
            "confidence": min(
                analysis.get("confidence", 0.0),
                agent_result.get("confidence", 0.0),
            ),
            "answer": agent_result.get("answer", ""),
            "results": agent_result.get("data", {}),
            "tool_calls": agent_result.get("tool_calls", []),
            "execution_time_ms": (
                analysis.get("execution_time_ms", 0)
                + agent_result.get("execution_time_ms", 0)
            ),
            "agent_result": agent_result,
            "selected_tools": agent_result.get("tool_calls", []),
        }

    # ========================================================================
    # Multi-Agent Collaboration Methods (Phase 4: User Story 2)
    # ========================================================================

    async def decompose_query(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Use LLM to decompose a complex query for multiple agents.
        
        **FULLY AGENTIC**: LLM decides if multi-agent is needed and how to decompose!
        """
        start_time = datetime.utcnow()
        
        try:
            # Prepare context summary
            context_summary = self._prepare_context_summary(context)
            
            # Ask LLM to decompose query
            prompt = self.MULTI_AGENT_DECOMPOSITION_PROMPT.format(
                query=query,
                context=context_summary
            )
            
            messages = [
                SystemMessage(content="You are an expert at decomposing complex queries for multi-agent systems."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse LLM response
            content = ""
            try:
                # Handle response content which can be str or list
                content = response.content if isinstance(response.content, str) else str(response.content)
                
                # Strip markdown code blocks if present (```json ... ``` or ```python ... ```)
                content = self._strip_markdown_code_blocks(content)
                
                decomposition_dict = self.decomposition_parser.parse(content)
                decomposition = MultiAgentDecomposition(**decomposition_dict)
            except Exception as e:
                logger.warning(f"Failed to parse decomposition response: {e}, content: {content[:200]}")
                # Fallback to single-agent
                decomposition = MultiAgentDecomposition(
                    is_multi_agent=False,
                    required_agents=["discovery"],
                    execution_strategy="single",
                    reasoning="Failed to parse LLM response, defaulting to single-agent",
                    sub_queries={"discovery": query}
                )
            
            execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Convert agent strings to AgentType enums
            required_agent_types = []
            for agent_str in decomposition.required_agents:
                try:
                    agent_type = AgentType(agent_str)
                    if agent_type in self.agents:
                        required_agent_types.append(agent_type)
                except ValueError:
                    logger.warning(f"Invalid agent type '{agent_str}', skipping")
            
            # If no valid agents, default to discovery
            if not required_agent_types:
                required_agent_types = [AgentType.DISCOVERY]
                decomposition.is_multi_agent = False
            
            # Build sub_queries dict with AgentType keys
            sub_queries_typed = {}
            for agent_type in required_agent_types:
                agent_str = agent_type.value
                sub_queries_typed[agent_type] = decomposition.sub_queries.get(agent_str, query)
            
            logger.info(
                f"LLM decomposition: {len(required_agent_types)} agents, strategy: {decomposition.execution_strategy}",
                extra={
                    "is_multi_agent": decomposition.is_multi_agent,
                    "required_agents": [a.value for a in required_agent_types],
                    "execution_strategy": decomposition.execution_strategy,
                }
            )
            
            return {
                "is_multi_agent": decomposition.is_multi_agent and len(required_agent_types) > 1,
                "required_agents": required_agent_types,
                "sub_queries": sub_queries_typed,
                "execution_strategy": decomposition.execution_strategy,
                "dependencies": {},  # LLM can be enhanced to specify dependencies
                "reasoning": decomposition.reasoning,
                "execution_time_ms": execution_time_ms,
            }
            
        except Exception as e:
            logger.error(f"LLM query decomposition failed: {e}", exc_info=True)
            # Fallback to single-agent
            return {
                "is_multi_agent": False,
                "required_agents": [AgentType.DISCOVERY],
                "sub_queries": {AgentType.DISCOVERY: query},
                "execution_strategy": "single",
                "dependencies": {},
                "reasoning": f"Decomposition failed: {str(e)}",
                "execution_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            }

    def _prepare_context_summary(self, context: Optional[Dict[str, Any]]) -> str:
        """Prepare a concise context summary for LLM prompts."""
        if not context:
            return "No previous context"
        
        summary_parts = []
        
        if "query_history" in context and context["query_history"]:
            recent_queries = context["query_history"][-3:]  # Last 3 queries
            summary_parts.append(f"Recent queries: {', '.join(recent_queries)}")
        
        if "entity_mentions" in context and context["entity_mentions"]:
            entities = []
            for entity_type, entity_ids in context["entity_mentions"].items():
                if entity_ids:
                    entities.append(f"{len(entity_ids)} {entity_type}(s)")
            if entities:
                summary_parts.append(f"Mentioned entities: {', '.join(entities)}")
        
        return " | ".join(summary_parts) if summary_parts else "No previous context"

    async def execute_parallel_agents(
        self,
        sub_queries: Dict[AgentType, str],
        context: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Dict[AgentType, Dict[str, Any]]:
        """
        Execute multiple agents in parallel with timeout management.
        """
        start_time = datetime.utcnow()
        
        # Create tasks for parallel execution
        tasks = []
        agent_types = []
        
        for agent_type, sub_query in sub_queries.items():
            if agent_type in self.agents:
                agent = self.agents[agent_type]
                tasks.append(agent.execute(query=sub_query, context=context))
                agent_types.append(agent_type)
            else:
                logger.warning(f"Agent {agent_type.value} not available, skipping")
        
        # Execute all agents in parallel with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Parallel agent execution timed out after {timeout}s")
            return {
                agent_type: {
                    "success": False,
                    "error": f"Execution timed out after {timeout}s",
                    "confidence": 0.0,
                }
                for agent_type in agent_types
            }
        
        # Map results back to agent types
        agent_results: Dict[AgentType, Dict[str, Any]] = {}
        for agent_type, result in zip(agent_types, results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agent_type.value} failed: {result}")
                agent_results[agent_type] = {
                    "success": False,
                    "error": str(result),
                    "confidence": 0.0,
                }
            elif isinstance(result, dict):
                agent_results[agent_type] = result
            else:
                agent_results[agent_type] = {
                    "success": False,
                    "error": "Unexpected result type",
                    "confidence": 0.0,
                }
        
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info(
            f"Parallel execution completed: {len(agent_results)} agents, {execution_time_ms}ms",
            extra={
                "agents": [a.value for a in agent_results.keys()],
                "execution_time_ms": execution_time_ms,
            },
        )
        
        return agent_results

    async def execute_sequential_agents(
        self,
        sub_queries: Dict[AgentType, str],
        dependencies: Dict[AgentType, List[AgentType]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[AgentType, Dict[str, Any]]:
        """
        Execute agents sequentially based on dependencies.
        """
        start_time = datetime.utcnow()
        agent_results: Dict[AgentType, Dict[str, Any]] = {}
        
        # Build execution order using topological sort
        execution_order = self._topological_sort(list(sub_queries.keys()), dependencies)
        
        logger.info(
            f"Sequential execution order: {[a.value for a in execution_order]}",
            extra={"execution_order": [a.value for a in execution_order]},
        )
        
        # Execute agents in order
        for agent_type in execution_order:
            if agent_type not in self.agents:
                logger.warning(f"Agent {agent_type.value} not available, skipping")
                continue
            
            agent = self.agents[agent_type]
            sub_query = sub_queries[agent_type]
            
            # Enrich context with results from dependencies
            enriched_context = context.copy() if context else {}
            if agent_type in dependencies:
                for dep_agent in dependencies[agent_type]:
                    if dep_agent in agent_results:
                        enriched_context[f"{dep_agent.value}_results"] = agent_results[dep_agent]
            
            try:
                result = await agent.execute(query=sub_query, context=enriched_context)
                agent_results[agent_type] = result
            except Exception as e:
                logger.error(f"Agent {agent_type.value} failed: {e}")
                agent_results[agent_type] = {
                    "success": False,
                    "error": str(e),
                    "confidence": 0.0,
                }
        
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info(
            f"Sequential execution completed: {len(agent_results)} agents, {execution_time_ms}ms",
            extra={
                "agents": [a.value for a in agent_results.keys()],
                "execution_time_ms": execution_time_ms,
            },
        )
        
        return agent_results

    def _topological_sort(
        self,
        agents: List[AgentType],
        dependencies: Dict[AgentType, List[AgentType]],
    ) -> List[AgentType]:
        """Perform topological sort to determine execution order."""
        in_degree: Dict[AgentType, int] = {agent: 0 for agent in agents}
        for agent, deps in dependencies.items():
            if agent in in_degree:
                in_degree[agent] = len(deps)
        
        queue = [agent for agent in agents if in_degree[agent] == 0]
        result = []
        
        while queue:
            agent = queue.pop(0)
            result.append(agent)
            
            for dependent, deps in dependencies.items():
                if agent in deps and dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        for agent in agents:
            if agent not in result:
                result.append(agent)
        
        return result

    def correlate_results_by_entity(
        self,
        agent_results: Dict[AgentType, Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Correlate multi-agent results by entity ID."""
        entity_map: Dict[str, Dict[str, Any]] = {}
        
        for agent_type, result in agent_results.items():
            if not result.get("success", True):
                continue
            
            data = result.get("data", {})
            entities = self._extract_entities(data)
            
            for entity_id, entity_data in entities.items():
                if entity_id not in entity_map:
                    entity_map[entity_id] = {
                        "entity_id": entity_id,
                        "entity_type": entity_data.get("entity_type", "unknown"),
                        "agent_data": {},
                    }
                
                entity_map[entity_id]["agent_data"][agent_type.value] = entity_data
        
        logger.info(
            f"Correlated results for {len(entity_map)} entities",
            extra={"entity_count": len(entity_map)},
        )
        
        return entity_map

    def _extract_entities(self, data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract entities with IDs from agent result data."""
        entities: Dict[str, Dict[str, Any]] = {}
        
        if isinstance(data, dict):
            for list_field in ["apis", "vulnerabilities", "predictions", "recommendations", "violations"]:
                if list_field in data and isinstance(data[list_field], list):
                    for item in data[list_field]:
                        if isinstance(item, dict):
                            entity_id = item.get("id") or item.get("api_id") or item.get("gateway_id")
                            if entity_id:
                                entities[entity_id] = {
                                    **item,
                                    "entity_type": list_field.rstrip("s"),
                                }
            
            if "id" in data:
                entity_id = data["id"]
                entities[entity_id] = {
                    **data,
                    "entity_type": data.get("type", "unknown"),
                }
        
        return entities

    def resolve_conflicts(
        self,
        agent_results: Dict[AgentType, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Resolve conflicts in inconsistent agent results."""
        conflicts = []
        resolved_data = {}
        
        entity_map = self.correlate_results_by_entity(agent_results)
        
        for entity_id, entity_info in entity_map.items():
            agent_data = entity_info["agent_data"]
            
            if len(agent_data) > 1:
                statuses = {}
                for agent_name, data in agent_data.items():
                    if "status" in data:
                        statuses[agent_name] = data["status"]
                
                if len(set(statuses.values())) > 1:
                    conflicts.append({
                        "entity_id": entity_id,
                        "field": "status",
                        "values": statuses,
                        "resolution": "most_recent",
                    })
                    resolved_data[entity_id] = list(agent_data.values())[0]
                else:
                    merged = {}
                    for data in agent_data.values():
                        merged.update(data)
                    resolved_data[entity_id] = merged
            else:
                resolved_data[entity_id] = list(agent_data.values())[0]
        
        logger.info(
            f"Conflict resolution: {len(conflicts)} conflicts found and resolved",
            extra={"conflict_count": len(conflicts)},
        )
        
        return {
            "resolved_entities": resolved_data,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
        }

    async def execute_multi_agent_workflow(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent workflow for complex queries using LLM decomposition.
        """
        start_time = datetime.utcnow()
        
        # Step 1: LLM decomposes query
        decomposition = await self.decompose_query(query, context)
        
        if not decomposition["is_multi_agent"]:
            # Fall back to single-agent workflow
            return await self.execute_single_agent_workflow(query, context)
        
        # Step 2: Execute agents based on LLM-determined strategy
        if decomposition["execution_strategy"] == "parallel":
            agent_results = await self.execute_parallel_agents(
                decomposition["sub_queries"],
                context,
            )
        else:  # sequential
            agent_results = await self.execute_sequential_agents(
                decomposition["sub_queries"],
                decomposition["dependencies"],
                context,
            )
        
        # Step 3: Correlate and resolve conflicts
        resolved = self.resolve_conflicts(agent_results)
        
        # Step 4: Synthesize final result
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        confidences = [
            result.get("confidence", 0.0)
            for result in agent_results.values()
            if result.get("success", True)
        ]
        overall_confidence = min(confidences) if confidences else 0.0
        
        return {
            "query_text": query,
            "is_multi_agent": True,
            "required_agents": [a.value for a in decomposition["required_agents"]],
            "execution_strategy": decomposition["execution_strategy"],
            "confidence": overall_confidence,
            "results": resolved["resolved_entities"],
            "conflicts": resolved["conflicts"],
            "agent_results": {k.value: v for k, v in agent_results.items()},
            "execution_time_ms": execution_time_ms,
            "reasoning": decomposition.get("reasoning", ""),
        }
    
    def _strip_markdown_code_blocks(self, content: str) -> str:
        """
        Strip markdown code blocks from LLM response.
        
        LLMs sometimes wrap JSON in ```json ... ``` or ```python ... ``` blocks.
        This method extracts the actual content.
        """
        import re
        
        # Pattern to match ```language\n...content...\n```
        pattern = r'```(?:json|python)?\s*\n(.*?)\n```'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        
        # If no code block found, return original content
        return content.strip()

    # ========================================================================
    # Iterative Multi-Step Coordinator Reasoning (Feature: 002-agentic-query)
    # ========================================================================

    async def execute_iterative_workflow(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 10,
        timeout_seconds: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Execute iterative coordinator workflow with LLM-based completion evaluation.
        
        The coordinator iterates through multiple steps:
        1. Select agent using LLM
        2. Execute agent
        3. Evaluate completion using LLM
        4. If not complete, enrich context and repeat
        
        Feature: 002-agentic-query (User Story 6)
        """
        start_time = datetime.utcnow()
        
        # Initialize coordinator state
        state = CoordinatorState(
            query=query,
            max_iterations=max_iterations,
            iteration=0,
        )
        
        logger.info(
            f"Starting iterative workflow for query: {query[:100]}",
            extra={"max_iterations": max_iterations, "timeout_seconds": timeout_seconds}
        )
        
        # Track previous results for no-progress detection
        previous_result_hash: Optional[str] = None
        no_progress_count = 0
        
        try:
            while state.iteration < max_iterations:
                state.iteration += 1
                iteration_start = datetime.utcnow()
                
                # Check timeout
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    logger.warning(f"Workflow timeout after {elapsed:.2f}s")
                    return self._build_iterative_result(
                        state=state,
                        termination_reason="timeout",
                        start_time=start_time,
                    )
                
                logger.info(f"Iteration {state.iteration}/{max_iterations}")
                
                # Step 1: LLM selects agent
                analysis = await self.analyze_query(
                    query=query,
                    context=self._build_iteration_context(state, context),
                )
                
                agent_type: AgentType = analysis["agent_type"]
                agent = self.agents[agent_type]
                
                # Step 2: Execute agent
                try:
                    agent_result = await agent.execute(
                        query=query,
                        context=self._build_iteration_context(state, context),
                    )
                    
                    # Store intermediate result
                    result_key = f"{agent_type.value}_iter_{state.iteration}"
                    state.intermediate_results[result_key] = agent_result
                    
                    # Add completed step description
                    step_desc = f"Iteration {state.iteration}: {agent_type.value} agent - {analysis['reasoning']}"
                    state.completed_steps.append(step_desc)
                    
                    # Detect no progress
                    result_hash = self._hash_result(agent_result)
                    if result_hash == previous_result_hash:
                        no_progress_count += 1
                        logger.warning(f"No progress detected (count: {no_progress_count})")
                        if no_progress_count >= 2:
                            logger.warning("Stopping due to no progress")
                            return self._build_iterative_result(
                                state=state,
                                termination_reason="no_progress",
                                start_time=start_time,
                            )
                    else:
                        no_progress_count = 0
                        previous_result_hash = result_hash
                    
                except Exception as e:
                    logger.error(f"Agent execution failed: {e}", exc_info=True)
                    state.intermediate_results[f"error_iter_{state.iteration}"] = {
                        "error": str(e),
                        "agent": agent_type.value,
                    }
                    continue
                
                # Step 3: LLM evaluates completion
                completion = await self._evaluate_completion(state, query)
                
                state.is_complete = completion.is_complete
                state.completion_reasoning = completion.reasoning
                state.completion_confidence = completion.confidence
                
                iteration_time = int((datetime.utcnow() - iteration_start).total_seconds() * 1000)
                state.total_execution_time_ms += iteration_time
                state.last_updated = datetime.utcnow()
                
                logger.info(
                    f"Iteration {state.iteration} complete: is_complete={completion.is_complete}, "
                    f"confidence={completion.confidence:.2f}",
                    extra={
                        "iteration": state.iteration,
                        "is_complete": completion.is_complete,
                        "confidence": completion.confidence,
                    }
                )
                
                # Step 4: Check if complete
                if completion.is_complete:
                    logger.info(f"Query complete after {state.iteration} iterations")
                    return self._build_iterative_result(
                        state=state,
                        termination_reason="complete",
                        start_time=start_time,
                    )
                
                # Add next action to state
                if completion.next_action:
                    state.next_actions.append(completion.next_action)
            
            # Max iterations reached
            logger.warning(f"Max iterations ({max_iterations}) reached")
            return self._build_iterative_result(
                state=state,
                termination_reason="max_iterations_reached",
                start_time=start_time,
            )
            
        except Exception as e:
            logger.error(f"Iterative workflow failed: {e}", exc_info=True)
            return self._build_iterative_result(
                state=state,
                termination_reason=f"error: {str(e)}",
                start_time=start_time,
            )

    async def _evaluate_completion(
        self,
        state: CoordinatorState,
        query: str,
    ) -> CompletionDecision:
        """
        Use LLM to evaluate if query is fully answered.
        
        Feature: 002-agentic-query
        """
        try:
            # Prepare context for LLM
            completed_steps_str = "\n".join(
                f"{i+1}. {step}" for i, step in enumerate(state.completed_steps)
            )
            
            # Get latest result
            latest_result = {}
            if state.intermediate_results:
                latest_key = list(state.intermediate_results.keys())[-1]
                latest_result = state.intermediate_results[latest_key]
            
            # Format intermediate results
            intermediate_str = json.dumps(state.intermediate_results, indent=2, default=str)
            if len(intermediate_str) > 1000:
                intermediate_str = intermediate_str[:1000] + "... (truncated)"
            
            prompt = self.COMPLETION_EVALUATION_PROMPT.format(
                query=query,
                completed_steps=completed_steps_str or "None yet",
                latest_results=json.dumps(latest_result, indent=2, default=str)[:500],
                intermediate_results=intermediate_str,
            )
            
            messages = [
                SystemMessage(content="You are an expert at evaluating query completion."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse LLM response
            content = response.content if isinstance(response.content, str) else str(response.content)
            content = self._strip_markdown_code_blocks(content)
            
            decision_dict = self.completion_parser.parse(content)
            decision = CompletionDecision(**decision_dict)
            
            return decision
            
        except Exception as e:
            logger.warning(f"Completion evaluation failed: {e}, assuming not complete")
            # Conservative fallback: assume not complete
            return CompletionDecision(
                is_complete=False,
                confidence=0.3,
                reasoning=f"Evaluation failed: {str(e)}",
                next_action="Continue with next iteration"
            )

    def _build_iteration_context(
        self,
        state: CoordinatorState,
        base_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build enriched context for next iteration.
        
        Feature: 002-agentic-query
        """
        context = base_context.copy() if base_context else {}
        
        # Add iteration state
        context["iteration"] = state.iteration
        context["completed_steps"] = state.completed_steps
        context["intermediate_results"] = state.intermediate_results
        
        # Add entity mentions from intermediate results
        for result in state.intermediate_results.values():
            if isinstance(result, dict) and "data" in result:
                entities = self._extract_entities(result["data"])
                for entity_id, entity_data in entities.items():
                    entity_type = entity_data.get("entity_type", "unknown")
                    if "entity_mentions" not in context:
                        context["entity_mentions"] = {}
                    if entity_type not in context["entity_mentions"]:
                        context["entity_mentions"][entity_type] = []
                    if entity_id not in context["entity_mentions"][entity_type]:
                        context["entity_mentions"][entity_type].append(entity_id)
        
        return context

    def _build_iterative_result(
        self,
        state: CoordinatorState,
        termination_reason: str,
        start_time: datetime,
    ) -> Dict[str, Any]:
        """
        Build final result from iterative workflow.
        
        Feature: 002-agentic-query
        """
        total_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Aggregate results from all iterations
        all_results = {}
        for key, result in state.intermediate_results.items():
            if isinstance(result, dict) and "data" in result:
                # Merge data from each iteration
                if not all_results:
                    all_results = result["data"]
                else:
                    # Merge lists
                    for list_key in ["apis", "vulnerabilities", "predictions", "recommendations"]:
                        if list_key in result["data"]:
                            if list_key not in all_results:
                                all_results[list_key] = []
                            all_results[list_key].extend(result["data"][list_key])
        
        return {
            "query_text": state.query,
            "mode": "iterative",
            "iterations": state.iteration,
            "is_complete": state.is_complete,
            "completion_confidence": state.completion_confidence,
            "completion_reasoning": state.completion_reasoning,
            "termination_reason": termination_reason,
            "completed_steps": state.completed_steps,
            "next_actions": state.next_actions,
            "results": all_results,
            "intermediate_results": state.intermediate_results,
            "execution_time_ms": total_time,
            "started_at": state.started_at.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
        }

    def _hash_result(self, result: Dict[str, Any]) -> str:
        """
        Create hash of result for no-progress detection.
        
        Feature: 002-agentic-query
        """
        import hashlib
        
        # Extract key data for hashing
        data_str = json.dumps(result.get("data", {}), sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()


# Made with Bob