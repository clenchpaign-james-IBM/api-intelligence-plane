"""
Agentic Query Service

Provides single-agent agentic query orchestration using the coordinator agent,
session context management, and existing query persistence models.

Enhanced with fallback mechanism for graceful degradation to OpenSearch.

Feature: 001-agentic-query
Phase 5: User Story 3 - Intelligent Fallback
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from uuid import UUID, uuid4

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.agents.query.compliance_agent import ComplianceAgent
from app.agents.query.coordinator_agent import CoordinatorAgent
from app.agents.query.discovery_agent import DiscoveryAgent
from app.agents.query.metrics_agent import MetricsAgent
from app.agents.query.optimization_agent import OptimizationAgent
from app.agents.query.prediction_agent import PredictionAgent
from app.agents.query.security_agent import SecurityAgent
from app.models.agent import AgentType, ExecutionMode, FallbackReason, FallbackTrigger
from app.models.query import InterpretedIntent, Query, QueryResults, QueryType
from app.services.context_manager import ContextManager
from app.services.fallback_manager import FallbackManager
from app.services.query_service import QueryService
from app.tools.tool_registry import ToolRegistry
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgenticQueryService:
    """
    Orchestrates single-agent query execution.

    This service wires together:
    - tool registry domain filtering
    - specialized agents
    - coordinator selection logic
    - session context lifecycle
    - query model creation with agentic metadata
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tool_registry: ToolRegistry,
        context_manager: Optional[ContextManager] = None,
        fallback_service: Optional[QueryService] = None,
        fallback_manager: Optional[FallbackManager] = None,
    ) -> None:
        """
        Initialize AgenticQueryService with fallback support.
        
        Args:
            llm: Language model for agent reasoning
            tool_registry: Registry of available tools
            context_manager: Session context manager
            fallback_service: OpenSearch query service for fallback (T067, T068)
            fallback_manager: Fallback decision manager (T067)
        """
        self.llm = llm
        self.tool_registry = tool_registry
        self.context_manager = context_manager or ContextManager()
        self.fallback_service = fallback_service  # T067, T068
        self.fallback_manager = fallback_manager or FallbackManager()  # T067
        
        # T071: Metrics tracking
        self.total_queries = 0
        self.fallback_queries = 0
        self.fallback_reasons_count: Dict[str, int] = {}

        self.discovery_agent = DiscoveryAgent(
            llm=self.llm,
            tools=self._domain_tools("discovery"),
        )
        self.metrics_agent = MetricsAgent(
            llm=self.llm,
            tools=self._domain_tools("metrics"),
        )
        self.security_agent = SecurityAgent(
            llm=self.llm,
            tools=self._domain_tools("security"),
        )
        self.compliance_agent = ComplianceAgent(
            llm=self.llm,
            tools=self._domain_tools("compliance"),
        )
        self.optimization_agent = OptimizationAgent(
            llm=self.llm,
            tools=self._domain_tools("optimization"),
        )
        self.prediction_agent = PredictionAgent(
            llm=self.llm,
            tools=self._domain_tools("prediction"),
        )

        self.coordinator = CoordinatorAgent(
            llm=self.llm,
            agents={
                self.discovery_agent.agent_type: self.discovery_agent,
                self.metrics_agent.agent_type: self.metrics_agent,
                self.security_agent.agent_type: self.security_agent,
                self.compliance_agent.agent_type: self.compliance_agent,
                self.optimization_agent.agent_type: self.optimization_agent,
                self.prediction_agent.agent_type: self.prediction_agent,
            },
        )

    async def process_query(
        self,
        query_text: str,
        session_id: UUID,
        user_id: Optional[str] = None,
        use_iterative: bool = True,
    ) -> Query:
        """
        Process a natural language query with the agentic workflow.
        
        Automatically detects if multi-agent collaboration is needed and
        routes to the appropriate workflow (single-agent, multi-agent, or iterative).
        
        T067-T071: Includes fallback mechanism with graceful degradation.
        Feature 002: Supports iterative multi-step reasoning (T027-T035)
        
        Args:
            query_text: Natural language query
            session_id: Session identifier for context
            user_id: Optional user identifier
            use_iterative: If True, use iterative coordinator workflow (Feature 002)
        """
        started_at = datetime.utcnow()
        start_time = time.time()
        context = self.context_manager.get_or_create(session_id)
        
        # T071: Track total queries
        self.total_queries += 1
        
        try:
            # T034: Route to iterative workflow if requested (Feature 002)
            if use_iterative:
                coordinator_result = await self.coordinator.execute_iterative_workflow(
                    query=query_text,
                    context={
                        "session_id": str(session_id),
                        "query_history": context.query_history,
                        "entity_mentions": context.entity_mentions,
                        "user_id": user_id,
                    },
                    max_iterations=10,
                    timeout_seconds=1800.0,
                )
                is_multi_agent = False
                is_iterative = True
            else:
                # Check if multi-agent collaboration is needed
                decomposition = await self.coordinator.decompose_query(
                    query=query_text,
                    context={
                        "session_id": str(session_id),
                        "query_history": context.query_history,
                        "entity_mentions": context.entity_mentions,
                        "user_id": user_id,
                    },
                )

                # Route to appropriate workflow
                if decomposition["is_multi_agent"]:
                    coordinator_result = await self.coordinator.execute_multi_agent_workflow(
                        query=query_text,
                        context={
                            "session_id": str(session_id),
                            "query_history": context.query_history,
                            "entity_mentions": context.entity_mentions,
                            "user_id": user_id,
                        },
                    )
                    is_multi_agent = True
                    is_iterative = False
                else:
                    coordinator_result = await self.coordinator.execute_single_agent_workflow(
                        query=query_text,
                        context={
                            "session_id": str(session_id),
                            "query_history": context.query_history,
                            "entity_mentions": context.entity_mentions,
                            "user_id": user_id,
                        },
                    )
                    is_multi_agent = False
                    is_iterative = False

            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # T067: Check if fallback should be triggered
            confidence = coordinator_result.get("confidence", 0.0)
            tool_invocations = self._collect_tool_invocations(coordinator_result, is_multi_agent)
            selected_tools = coordinator_result.get("selected_tools", [])
            
            should_fallback, fallback_reason, fallback_message = self.fallback_manager.should_fallback(
                confidence=confidence,
                tool_invocations=tool_invocations,
                elapsed_time=elapsed_time,
                error=None,
                selected_tools=selected_tools,
            )
            
            # T068: Graceful degradation to OpenSearch if fallback triggered
            if should_fallback:
                logger.warning(
                    f"Fallback triggered for query: {fallback_message}",
                    extra={
                        "session_id": str(session_id),
                        "reason": fallback_reason.value if fallback_reason else None,
                        "confidence": confidence,
                        "elapsed_time": elapsed_time,
                    }
                )
                
                # T069, T070, T071: Log fallback and return fallback query
                return await self._handle_fallback(
                    query_text=query_text,
                    session_id=session_id,
                    user_id=user_id,
                    fallback_reason=fallback_reason,
                    fallback_message=fallback_message or "Fallback triggered",
                    coordinator_result=coordinator_result,
                    started_at=started_at,
                    elapsed_time=elapsed_time,
                )

            # T035: Process results based on workflow type
            if is_iterative:
                query = await self._process_iterative_result(
                    query_text=query_text,
                    session_id=session_id,
                    user_id=user_id,
                    coordinator_result=coordinator_result,
                    started_at=started_at,
                )
            elif is_multi_agent:
                query = await self._process_multi_agent_result(
                    query_text=query_text,
                    session_id=session_id,
                    user_id=user_id,
                    coordinator_result=coordinator_result,
                    started_at=started_at,
                )
            else:
                query = await self._process_single_agent_result(
                    query_text=query_text,
                    session_id=session_id,
                    user_id=user_id,
                    coordinator_result=coordinator_result,
                    started_at=started_at,
                )

            self.log_agent_activity(query)
            return query
            
        except Exception as e:
            # T066, T068: Handle exceptions with fallback
            logger.error(
                f"Agentic workflow failed: {e}",
                extra={
                    "session_id": str(session_id),
                    "query_text": query_text,
                },
                exc_info=True,
            )
            
            elapsed_time = time.time() - start_time
            
            # Check if LLM unavailable
            should_fallback, fallback_reason, fallback_message = self.fallback_manager.should_fallback(
                confidence=0.0,
                tool_invocations=[],
                elapsed_time=elapsed_time,
                error=e,
                selected_tools=None,
            )
            
            if should_fallback and self.fallback_service:
                return await self._handle_fallback(
                    query_text=query_text,
                    session_id=session_id,
                    user_id=user_id,
                    fallback_reason=fallback_reason,
                    fallback_message=f"Exception: {fallback_message or str(e)}",
                    coordinator_result={},
                    started_at=started_at,
                    elapsed_time=elapsed_time,
                )
            
            # Re-raise if no fallback service available
            raise

    async def _process_single_agent_result(
        self,
        query_text: str,
        session_id: UUID,
        user_id: Optional[str],
        coordinator_result: Dict[str, Any],
        started_at: datetime,
    ) -> Query:
        """Process single-agent workflow result."""
        selected_agent = coordinator_result["selected_agent"]
        agent_result = coordinator_result["agent_result"]
        agent_instance = self.coordinator.agents[selected_agent]

        confidence = self.calculate_confidence_score(coordinator_result)
        execution_time_ms = int(
            (datetime.utcnow() - started_at).total_seconds() * 1000
        )

        results_payload = self._normalize_results(coordinator_result)
        self.update_context(
            session_id=session_id,
            query_text=query_text,
            results=results_payload,
        )

        query = Query(
            session_id=session_id,
            user_id=user_id,
            query_text=query_text,
            query_type=self._infer_query_type(selected_agent.value),
            interpreted_intent=InterpretedIntent(
                action="analyze",
                entities=[selected_agent.value],
                filters={},
                time_range=None,
            ),
            opensearch_query=None,
            results=QueryResults(
                data=results_payload.get("tool_results", []),
                count=len(results_payload.get("tool_results", [])),
                execution_time=execution_time_ms,
                aggregations={
                    "selected_agent": selected_agent.value,
                    "tool_calls": coordinator_result.get("tool_calls", []),
                },
            ),
            response_text=coordinator_result.get("answer", ""),
            confidence_score=confidence,
            execution_time_ms=execution_time_ms,
            feedback=None,
            feedback_comment=None,
            follow_up_queries=self.generate_follow_up_queries(selected_agent.value),
            metadata={
                "agentic": True,
                "selected_agent": selected_agent.value,
                "coordinator_reasoning": coordinator_result.get("reasoning"),
            },
            execution_mode=ExecutionMode.AGENTIC,
            agent_decisions=list(agent_instance.decisions),
            tool_invocations=list(agent_instance.tool_invocations),
            fallback_reason=None,
        )

        return query

    async def _process_multi_agent_result(
        self,
        query_text: str,
        session_id: UUID,
        user_id: Optional[str],
        coordinator_result: Dict[str, Any],
        started_at: datetime,
    ) -> Query:
        """
        T058: Process multi-agent workflow result with cross-domain merging.
        """
        execution_time_ms = int(
            (datetime.utcnow() - started_at).total_seconds() * 1000
        )

        # Merge results from multiple agents
        merged_results = self.merge_cross_domain_results(coordinator_result)
        
        # T059: Generate natural language response for multi-agent results
        response_text = await self.generate_multi_agent_response(
            query_text=query_text,
            coordinator_result=coordinator_result,
            merged_results=merged_results,
        )
        
        # T060: Generate follow-up queries based on multi-agent results
        follow_up_queries = self.generate_multi_agent_follow_ups(
            coordinator_result=coordinator_result,
            merged_results=merged_results,
        )

        # Collect all agent decisions and tool invocations
        all_decisions = []
        all_tool_invocations = []
        for agent_type in coordinator_result.get("required_agents", []):
            agent_type_enum = AgentType(agent_type)
            if agent_type_enum in self.coordinator.agents:
                agent_instance = self.coordinator.agents[agent_type_enum]
                all_decisions.extend(agent_instance.decisions)
                all_tool_invocations.extend(agent_instance.tool_invocations)

        confidence = coordinator_result.get("confidence", 0.0)

        self.update_context(
            session_id=session_id,
            query_text=query_text,
            results=merged_results,
        )

        query = Query(
            session_id=session_id,
            user_id=user_id,
            query_text=query_text,
            query_type=QueryType.GENERAL,  # Multi-agent queries are cross-domain
            interpreted_intent=InterpretedIntent(
                action="analyze",
                entities=coordinator_result.get("required_agents", []),
                filters={},
                time_range=None,
            ),
            opensearch_query=None,
            results=QueryResults(
                data=merged_results.get("entities", []),
                count=len(merged_results.get("entities", [])),
                execution_time=execution_time_ms,
                aggregations={
                    "required_agents": coordinator_result.get("required_agents", []),
                    "execution_strategy": coordinator_result.get("execution_strategy"),
                    "conflicts": coordinator_result.get("conflicts", []),
                },
            ),
            response_text=response_text,
            confidence_score=confidence,
            execution_time_ms=execution_time_ms,
            feedback=None,
            feedback_comment=None,
            follow_up_queries=follow_up_queries,
            metadata={
                "agentic": True,
                "is_multi_agent": True,
                "required_agents": coordinator_result.get("required_agents", []),
                "execution_strategy": coordinator_result.get("execution_strategy"),
                "conflict_count": len(coordinator_result.get("conflicts", [])),
            },
            execution_mode=ExecutionMode.AGENTIC,
            agent_decisions=all_decisions,
            tool_invocations=all_tool_invocations,
            fallback_reason=None,
        )

        return query

    async def _process_iterative_result(
        self,
        query_text: str,
        session_id: UUID,
        user_id: Optional[str],
        coordinator_result: Dict[str, Any],
        started_at: datetime,
    ) -> Query:
        """
        T035: Process iterative coordinator workflow result.
        
        Feature: 002-agentic-query (User Story 6)
        """
        execution_time_ms = coordinator_result.get("execution_time_ms", 0)
        
        # Extract results from all iterations
        results_payload = coordinator_result.get("results", {})
        
        # Update context with final results
        self.update_context(
            session_id=session_id,
            query_text=query_text,
            results=results_payload,
        )
        
        # Collect all agent decisions and tool invocations from intermediate results
        all_decisions = []
        all_tool_invocations = []
        for result_key, result in coordinator_result.get("intermediate_results", {}).items():
            if isinstance(result, dict):
                # Extract agent type from result key (e.g., "discovery_iter_1")
                if "_iter_" in result_key:
                    agent_name = result_key.split("_iter_")[0]
                    try:
                        agent_type = AgentType(agent_name)
                        if agent_type in self.coordinator.agents:
                            agent_instance = self.coordinator.agents[agent_type]
                            all_decisions.extend(agent_instance.decisions)
                            all_tool_invocations.extend(agent_instance.tool_invocations)
                    except ValueError:
                        pass
        
        # Generate natural language response
        response_text = self._generate_iterative_response(coordinator_result)
        
        # Generate follow-up queries
        follow_up_queries = self._generate_iterative_follow_ups(coordinator_result)
        
        query = Query(
            session_id=session_id,
            user_id=user_id,
            query_text=query_text,
            query_type=QueryType.GENERAL,
            interpreted_intent=InterpretedIntent(
                action="analyze",
                entities=[],
                filters={},
                time_range=None,
            ),
            opensearch_query=None,
            results=QueryResults(
                data=results_payload.get("apis", []) or results_payload.get("entities", []),
                count=len(results_payload.get("apis", []) or results_payload.get("entities", [])),
                execution_time=execution_time_ms,
                aggregations={
                    "mode": "iterative",
                    "iterations": coordinator_result.get("iterations", 0),
                    "completed_steps": coordinator_result.get("completed_steps", []),
                    "termination_reason": coordinator_result.get("termination_reason"),
                },
            ),
            response_text=response_text,
            confidence_score=coordinator_result.get("completion_confidence", 0.0),
            execution_time_ms=execution_time_ms,
            feedback=None,
            feedback_comment=None,
            follow_up_queries=follow_up_queries,
            metadata={
                "agentic": True,
                "is_iterative": True,
                "iterations": coordinator_result.get("iterations", 0),
                "is_complete": coordinator_result.get("is_complete", False),
                "completion_reasoning": coordinator_result.get("completion_reasoning", ""),
                "termination_reason": coordinator_result.get("termination_reason"),
                "completed_steps": coordinator_result.get("completed_steps", []),
            },
            execution_mode=ExecutionMode.AGENTIC,
            agent_decisions=all_decisions,
            tool_invocations=all_tool_invocations,
            fallback_reason=None,
        )
        
        return query

    def _generate_iterative_response(self, coordinator_result: Dict[str, Any]) -> str:
        """
        Generate natural language response for iterative workflow.
        
        Feature: 002-agentic-query
        """
        iterations = coordinator_result.get("iterations", 0)
        is_complete = coordinator_result.get("is_complete", False)
        completion_reasoning = coordinator_result.get("completion_reasoning", "")
        completed_steps = coordinator_result.get("completed_steps", [])
        
        response_parts = []
        
        # Opening statement
        if is_complete:
            response_parts.append(
                f"I completed your query in {iterations} iteration{'s' if iterations != 1 else ''}."
            )
        else:
            response_parts.append(
                f"I processed your query through {iterations} iteration{'s' if iterations != 1 else ''}, "
                f"but couldn't fully complete it."
            )
        
        # Completion reasoning
        if completion_reasoning:
            response_parts.append(completion_reasoning)
        
        # Steps summary
        if completed_steps:
            response_parts.append(
                f"Steps completed: {len(completed_steps)}"
            )
        
        return " ".join(response_parts)

    def _generate_iterative_follow_ups(self, coordinator_result: Dict[str, Any]) -> List[str]:
        """
        Generate follow-up queries for iterative workflow.
        
        Feature: 002-agentic-query
        """
        follow_ups = []
        
        is_complete = coordinator_result.get("is_complete", False)
        next_actions = coordinator_result.get("next_actions", [])
        
        if not is_complete and next_actions:
            # Suggest continuing with next actions
            for action in next_actions[:2]:
                follow_ups.append(action)
        
        # Add generic follow-ups
        follow_ups.extend([
            "Show me more details",
            "What else can you tell me?",
        ])
        
        return follow_ups[:4]

    def calculate_confidence_score(self, coordinator_result: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the workflow."""
        return max(0.0, min(1.0, coordinator_result.get("confidence", 0.0)))

    def log_agent_activity(self, query: Query) -> None:
        """Log decisions and tool activity for observability."""
        logger.info(
            "Agentic query processed",
            extra={
                "query_id": str(query.id),
                "session_id": str(query.session_id),
                "execution_mode": (
                    query.execution_mode.value if query.execution_mode else None
                ),
                "decision_count": len(query.agent_decisions or []),
                "tool_invocation_count": len(query.tool_invocations or []),
                "confidence_score": query.confidence_score,
            },
        )

    def update_context(
        self,
        session_id: UUID,
        query_text: str,
        results: Dict[str, Any],
    ) -> None:
        """
        Update conversational context after query completion (T082).
        
        Extracts entities from results and updates session context for
        future reference resolution by the LLM.
        
        Args:
            session_id: Session identifier
            query_text: Query that was executed
            results: Query results containing entities
        """
        context = self.context_manager.get_or_create(session_id)
        
        # T077: Add query to history (max 10)
        context.add_query(query_text)
        
        # T078: Cache results for reference
        context.update_results(results)
        
        # T081: Extract entities from results for context tracking
        self._extract_and_track_entities(session_id, results, context)
        
        self.context_manager.update(session_id, context)
        
        logger.debug(
            f"Updated context for session {session_id}",
            extra={
                "session_id": str(session_id),
                "query_count": len(context.query_history),
                "entity_types": list(context.entity_mentions.keys())
            }
        )
    
    def _extract_and_track_entities(
        self,
        session_id: UUID,
        results: Dict[str, Any],
        context: Any,
    ) -> None:
        """
        Extract entities from query results and track them in context (T081).
        
        This enables the LLM to understand what entities were mentioned in
        previous queries when resolving references like "those APIs" or "them".
        
        Args:
            session_id: Session identifier
            results: Query results to extract entities from
            context: Query context to update
        """
        # Extract APIs
        if "apis" in results or "api_list" in results:
            apis = results.get("apis") or results.get("api_list", [])
            for api in apis:
                if isinstance(api, dict):
                    api_id = api.get("id") or api.get("api_id") or api.get("name")
                    if api_id:
                        context.add_entity_mention("api", str(api_id))
        
        # Extract gateways
        if "gateways" in results or "gateway_list" in results:
            gateways = results.get("gateways") or results.get("gateway_list", [])
            for gateway in gateways:
                if isinstance(gateway, dict):
                    gw_id = gateway.get("id") or gateway.get("gateway_id") or gateway.get("name")
                    if gw_id:
                        context.add_entity_mention("gateway", str(gw_id))
        
        # Extract vulnerabilities
        if "vulnerabilities" in results or "findings" in results:
            vulns = results.get("vulnerabilities") or results.get("findings", [])
            for vuln in vulns:
                if isinstance(vuln, dict):
                    vuln_id = vuln.get("id") or vuln.get("finding_id")
                    if vuln_id:
                        context.add_entity_mention("vulnerability", str(vuln_id))
        
        # Extract predictions
        if "predictions" in results:
            predictions = results.get("predictions", [])
            for pred in predictions:
                if isinstance(pred, dict):
                    pred_id = pred.get("id") or pred.get("prediction_id")
                    if pred_id:
                        context.add_entity_mention("prediction", str(pred_id))
        
        # Extract recommendations
        if "recommendations" in results:
            recommendations = results.get("recommendations", [])
            for rec in recommendations:
                if isinstance(rec, dict):
                    rec_id = rec.get("id") or rec.get("recommendation_id")
                    if rec_id:
                        context.add_entity_mention("recommendation", str(rec_id))
        
        logger.debug(
            f"Extracted entities from results for session {session_id}",
            extra={
                "session_id": str(session_id),
                "entity_counts": {
                    entity_type: len(entities)
                    for entity_type, entities in context.entity_mentions.items()
                }
            }
        )

    def generate_follow_up_queries(self, agent_domain: str) -> list[str]:
        """Generate simple follow-up suggestions by selected domain."""
        suggestions = {
            "security": [
                "Show me the highest severity findings",
                "Which APIs are affected by these vulnerabilities?",
            ],
            "compliance": [
                "Show me the most severe compliance violations",
                "Which APIs are out of compliance?",
            ],
            "optimization": [
                "Which recommendations have the highest impact?",
                "Show me rate limiting related recommendations",
            ],
            "prediction": [
                "Which APIs are most likely to fail next?",
                "Show me the highest confidence predictions",
            ],
            "metrics": [
                "Which APIs have the highest latency?",
                "Show me the performance summary for the last 24 hours",
            ],
            "discovery": [
                "Show me more details for a specific API",
                "Which gateways are currently connected?",
            ],
        }
        return suggestions.get(agent_domain, [])

    def merge_cross_domain_results(
        self,
        coordinator_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        T058: Merge results from multiple agents across different domains.
        
        Combines data from security, metrics, compliance, etc. into a unified view.
        """
        merged = {
            "entities": [],
            "summary": {},
            "by_agent": {},
        }

        # Get resolved entities from coordinator
        resolved_entities = coordinator_result.get("results", {})
        
        # Convert entity map to list
        if isinstance(resolved_entities, dict):
            for entity_id, entity_data in resolved_entities.items():
                merged["entities"].append(entity_data)
        
        # Organize by agent for detailed view
        agent_results = coordinator_result.get("agent_results", {})
        for agent_name, result in agent_results.items():
            if result.get("success", True):
                merged["by_agent"][agent_name] = result.get("data", {})
        
        # Create summary statistics
        merged["summary"] = {
            "total_entities": len(merged["entities"]),
            "agents_involved": len(agent_results),
            "execution_strategy": coordinator_result.get("execution_strategy"),
            "conflicts_resolved": len(coordinator_result.get("conflicts", [])),
        }
        
        return merged

    async def generate_multi_agent_response(
        self,
        query_text: str,
        coordinator_result: Dict[str, Any],
        merged_results: Dict[str, Any],
    ) -> str:
        """
        T059: Generate natural language response for multi-agent results.
        
        Creates a coherent narrative that synthesizes findings from multiple agents.
        """
        required_agents = coordinator_result.get("required_agents", [])
        entity_count = merged_results["summary"]["total_entities"]
        conflicts = coordinator_result.get("conflicts", [])
        
        # Build response parts
        response_parts = []
        
        # Opening statement
        response_parts.append(
            f"I analyzed your query using {len(required_agents)} specialized agents "
            f"({', '.join(required_agents)})."
        )
        
        # Entity summary
        if entity_count > 0:
            response_parts.append(
                f"Found {entity_count} relevant entities across all domains."
            )
        
        # Agent-specific findings
        agent_results = coordinator_result.get("agent_results", {})
        for agent_name, result in agent_results.items():
            if result.get("success", True) and result.get("answer"):
                response_parts.append(f"{agent_name.title()}: {result['answer']}")
        
        # Conflict resolution note
        if conflicts:
            response_parts.append(
                f"Note: Resolved {len(conflicts)} data conflicts between agents."
            )
        
        return " ".join(response_parts)

    def generate_multi_agent_follow_ups(
        self,
        coordinator_result: Dict[str, Any],
        merged_results: Dict[str, Any],
    ) -> List[str]:
        """
        T060: Generate follow-up query suggestions based on multi-agent results.
        
        Suggests queries that drill deeper into specific agent findings or
        explore relationships between domains.
        """
        follow_ups = []
        required_agents = coordinator_result.get("required_agents", [])
        
        # Cross-domain follow-ups
        if "security" in required_agents and "metrics" in required_agents:
            follow_ups.append("Show me performance impact of security vulnerabilities")
        
        if "compliance" in required_agents and "security" in required_agents:
            follow_ups.append("Which compliance violations are security-related?")
        
        if "optimization" in required_agents and "metrics" in required_agents:
            follow_ups.append("What's the expected performance improvement from recommendations?")
        
        if "prediction" in required_agents:
            follow_ups.append("Show me the highest risk predictions")
        
        # Agent-specific drill-downs
        for agent_name in required_agents:
            agent_suggestions = self.generate_follow_up_queries(agent_name)
            if agent_suggestions:
                follow_ups.append(agent_suggestions[0])  # Add first suggestion
        
        # Limit to 4 suggestions
        return follow_ups[:4]

    def _normalize_results(self, coordinator_result: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize coordinator payload for QueryResults storage."""
        results = coordinator_result.get("results")
        if isinstance(results, dict):
            return results
        return {"tool_results": []}

    def _domain_tools(self, domain: str) -> List[BaseTool]:
        """Return domain tools cast to the BaseTool type expected by agents."""
        return cast(List[BaseTool], self.tool_registry.get_tools_by_domain(domain))

    def _infer_query_type(self, agent_domain: str) -> QueryType:
        """Map selected agent domain to existing query type enum."""
        mapping = {
            "security": QueryType.SECURITY,
            "compliance": QueryType.COMPLIANCE,
            "optimization": QueryType.PERFORMANCE,
            "prediction": QueryType.PREDICTION,
            "metrics": QueryType.PERFORMANCE,
            "discovery": QueryType.GENERAL,
        }
        return mapping.get(agent_domain, QueryType.GENERAL)
    def _collect_tool_invocations(
        self,
        coordinator_result: Dict[str, Any],
        is_multi_agent: bool,
    ) -> List:
        """
        Collect all tool invocations from coordinator result.
        
        Helper method for fallback decision logic.
        """
        tool_invocations = []
        
        if is_multi_agent:
            # Collect from all agents
            for agent_type in coordinator_result.get("required_agents", []):
                agent_type_enum = AgentType(agent_type)
                if agent_type_enum in self.coordinator.agents:
                    agent_instance = self.coordinator.agents[agent_type_enum]
                    tool_invocations.extend(agent_instance.tool_invocations)
        else:
            # Collect from single agent
            selected_agent = coordinator_result.get("selected_agent")
            if selected_agent and selected_agent in self.coordinator.agents:
                agent_instance = self.coordinator.agents[selected_agent]
                tool_invocations.extend(agent_instance.tool_invocations)
        
        return tool_invocations
    
    async def _handle_fallback(
        self,
        query_text: str,
        session_id: UUID,
        user_id: Optional[str],
        fallback_reason: Optional[FallbackReason],
        fallback_message: str,
        coordinator_result: Dict[str, Any],
        started_at: datetime,
        elapsed_time: float,
    ) -> Query:
        """
        T068, T069, T070, T071: Handle fallback to OpenSearch query service.
        
        Gracefully degrades to OpenSearch when agentic workflow fails or
        triggers fallback conditions.
        """
        # T071: Track fallback metrics
        self.fallback_queries += 1
        if fallback_reason:
            reason_key = fallback_reason.value
            self.fallback_reasons_count[reason_key] = (
                self.fallback_reasons_count.get(reason_key, 0) + 1
            )
        
        # T068: Use fallback service if available
        if self.fallback_service:
            try:
                logger.info(
                    f"Using OpenSearch fallback for query",
                    extra={
                        "session_id": str(session_id),
                        "reason": fallback_reason.value if fallback_reason else "unknown",
                    }
                )
                
                # Call OpenSearch query service
                fallback_query = await self.fallback_service.process_query(
                    query_text=query_text,
                    session_id=session_id,
                    user_id=user_id,
                )
                
                # T070: Update with fallback metadata
                fallback_query.execution_mode = ExecutionMode.FALLBACK
                fallback_query.fallback_reason = fallback_reason
                fallback_query.metadata = fallback_query.metadata or {}
                fallback_query.metadata.update({
                    "fallback_triggered": True,
                    "fallback_message": fallback_message,
                    "agentic_confidence": coordinator_result.get("confidence", 0.0),
                    "agentic_elapsed_time": elapsed_time,
                })
                
                # T070: Log fallback trigger to OpenSearch
                await self._log_fallback_trigger(
                    query_id=fallback_query.id,
                    query_text=query_text,
                    session_id=session_id,
                    fallback_reason=fallback_reason,
                    fallback_message=fallback_message,
                    coordinator_result=coordinator_result,
                    elapsed_time=elapsed_time,
                )
                
                return fallback_query
                
            except Exception as e:
                logger.error(
                    f"Fallback to OpenSearch failed: {e}",
                    extra={"session_id": str(session_id)},
                    exc_info=True,
                )
                # Fall through to create error query
        
        # T070: Create fallback query without OpenSearch service
        execution_time_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        
        query = Query(
            session_id=session_id,
            user_id=user_id,
            query_text=query_text,
            query_type=QueryType.GENERAL,
            interpreted_intent=InterpretedIntent(
                action="fallback",
                entities=[],
                filters={},
                time_range=None,
            ),
            opensearch_query=None,
            results=QueryResults(
                data=[],
                count=0,
                execution_time=execution_time_ms,
                aggregations={},
            ),
            response_text=f"Unable to process query: {fallback_message}",
            confidence_score=0.0,
            execution_time_ms=execution_time_ms,
            feedback=None,
            feedback_comment=None,
            follow_up_queries=[],
            metadata={
                "fallback_triggered": True,
                "fallback_message": fallback_message,
                "no_fallback_service": self.fallback_service is None,
            },
            execution_mode=ExecutionMode.FALLBACK,
            agent_decisions=[],
            tool_invocations=[],
            fallback_reason=fallback_reason,
        )
        
        # T070: Log fallback trigger
        await self._log_fallback_trigger(
            query_id=query.id,
            query_text=query_text,
            session_id=session_id,
            fallback_reason=fallback_reason,
            fallback_message=fallback_message,
            coordinator_result=coordinator_result,
            elapsed_time=elapsed_time,
        )
        
        return query
    
    async def _log_fallback_trigger(
        self,
        query_id: UUID,
        query_text: str,
        session_id: UUID,
        fallback_reason: Optional[FallbackReason],
        fallback_message: str,
        coordinator_result: Dict[str, Any],
        elapsed_time: float,
    ) -> None:
        """
        T070: Log fallback trigger to OpenSearch for analytics.
        
        Uses FallbackManager to persist fallback trigger to OpenSearch.
        """
        try:
            # Collect tool invocations
            tool_invocations = self._collect_tool_invocations(
                coordinator_result,
                coordinator_result.get("is_multi_agent", False),
            )
            
            # Collect metadata
            metadata = {
                "session_id": str(session_id),
                "last_agent": coordinator_result.get("selected_agent", {}).get("value") if coordinator_result.get("selected_agent") else None,
                "attempted_tools": coordinator_result.get("selected_tools", []),
                "coordinator_reasoning": coordinator_result.get("reasoning"),
                "is_multi_agent": coordinator_result.get("is_multi_agent", False),
            }
            
            # T070: Use FallbackManager to log to OpenSearch
            await self.fallback_manager.log_fallback_trigger(
                query_id=query_id,
                query_text=query_text,
                reason=fallback_reason or FallbackReason.LLM_UNAVAILABLE,
                message=fallback_message,
                confidence=coordinator_result.get("confidence", 0.0),
                tool_invocations=tool_invocations,
                elapsed_time=elapsed_time,
                metadata=metadata,
            )
            
            logger.info(
                "Fallback trigger logged to OpenSearch",
                extra={
                    "query_id": str(query_id),
                    "reason": fallback_reason.value if fallback_reason else "unknown",
                }
            )
            
        except Exception as e:
            logger.error(
                f"Failed to log fallback trigger: {e}",
                extra={"query_id": str(query_id)},
                exc_info=True,
            )
    
    def get_fallback_statistics(self) -> Dict[str, Any]:
        """
        T071: Get fallback rate metrics for monitoring.
        
        Returns statistics about fallback usage for observability.
        """
        stats = self.fallback_manager.get_fallback_statistics(
            total_queries=self.total_queries,
            fallback_queries=self.fallback_queries,
        )
        
        stats["fallback_reasons"] = self.fallback_reasons_count.copy()
        
        return stats


# Made with Bob