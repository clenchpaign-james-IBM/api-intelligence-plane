"""
Agentic Query Service - Agent Module

This module contains all agent implementations for the agentic natural language
query service. Agents autonomously select and invoke appropriate tools to answer
user queries.

Architecture:
- CoordinatorAgent: Orchestrates multi-agent workflows
- Specialized Agents: Domain-specific agents (discovery, metrics, security, etc.)
- BaseAgent: Abstract base class for all agents

Feature: 001-agentic-query
"""

from app.agents.query.base_agent import BaseAgent

__all__ = ["BaseAgent"]

# Made with Bob
