"""
Agentic Query Service Agents

This module contains specialized agents for the agentic natural language query service.
These agents handle user queries by autonomously selecting and invoking appropriate tools.

Feature: 001-agentic-query

Agents:
- BaseAgent: Abstract base class for all query agents
- DiscoveryAgent: Handles API discovery and gateway management queries
- MetricsAgent: Handles performance and analytics queries
- SecurityAgent: Handles security and vulnerability queries
- ComplianceAgent: Handles compliance and audit queries
- OptimizationAgent: Handles optimization and rate limiting queries
- PredictionAgent: Handles failure prediction queries
- CoordinatorAgent: Orchestrates multi-agent workflows
"""

from app.agents.query.base_agent import BaseAgent
from app.agents.query.compliance_agent import ComplianceAgent
from app.agents.query.discovery_agent import DiscoveryAgent
from app.agents.query.metrics_agent import MetricsAgent
from app.agents.query.optimization_agent import OptimizationAgent
from app.agents.query.prediction_agent import PredictionAgent
from app.agents.query.security_agent import SecurityAgent

__all__ = [
    "BaseAgent",
    "ComplianceAgent",
    "DiscoveryAgent",
    "MetricsAgent",
    "OptimizationAgent",
    "PredictionAgent",
    "SecurityAgent",
]

# Made with Bob
