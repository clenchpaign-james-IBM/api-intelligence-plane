"""
Tracked Tool Wrapper - Integrates tool execution with BaseAgent tracking

This wrapper ensures that all tool invocations are properly logged
through BaseAgent's observability infrastructure, even when tools
are invoked automatically by create_agent().

Feature: 001-agentic-query
"""

from datetime import datetime
from typing import Any, Dict, Optional

from langchain_core.tools import BaseTool

from app.utils.logging import get_logger

logger = get_logger(__name__)


class TrackedTool(BaseTool):
    """
    Wrapper for RouterTool that integrates with BaseAgent tracking.
    
    This wrapper intercepts tool invocations to log them through
    BaseAgent's log_tool_invocation() method, providing accurate
    timing and execution details.
    
    Usage:
        original_tool = ListAPIsTool(...)
        tracked_tool = TrackedTool.wrap(original_tool, agent)
    """
    
    wrapped_tool: BaseTool
    agent: Optional[Any] = None  # BaseAgent instance
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def wrap(cls, tool: BaseTool, agent: Optional[Any] = None) -> "TrackedTool":
        """
        Wrap a tool with tracking capabilities.
        
        Args:
            tool: The tool to wrap
            agent: BaseAgent instance for logging (optional)
            
        Returns:
            TrackedTool instance
        """
        return cls(
            name=tool.name,
            description=tool.description,
            wrapped_tool=tool,
            agent=agent,
        )
    
    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous execution with tracking."""
        start_time = datetime.utcnow()
        
        try:
            # Execute the wrapped tool
            result = self.wrapped_tool._run(*args, **kwargs)
            
            # Calculate execution time
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Log invocation if agent is available
            if self.agent:
                self.agent.log_tool_invocation(
                    tool_name=self.name,
                    parameters=kwargs,
                    result=result if isinstance(result, dict) else {"output": result},
                    execution_time_ms=execution_time_ms,
                    success=True,
                    error=None,
                )
            
            return result
            
        except Exception as e:
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Log failed invocation if agent is available
            if self.agent:
                self.agent.log_tool_invocation(
                    tool_name=self.name,
                    parameters=kwargs,
                    result=None,
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error=str(e),
                )
            
            raise
    
    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronous execution with tracking."""
        start_time = datetime.utcnow()
        
        try:
            # Execute the wrapped tool
            result = await self.wrapped_tool._arun(*args, **kwargs)
            
            # Calculate execution time
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Log invocation if agent is available
            if self.agent:
                self.agent.log_tool_invocation(
                    tool_name=self.name,
                    parameters=kwargs,
                    result=result if isinstance(result, dict) else {"output": result},
                    execution_time_ms=execution_time_ms,
                    success=True,
                    error=None,
                )
            
            return result
            
        except Exception as e:
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            # Log failed invocation if agent is available
            if self.agent:
                self.agent.log_tool_invocation(
                    tool_name=self.name,
                    parameters=kwargs,
                    result=None,
                    execution_time_ms=execution_time_ms,
                    success=False,
                    error=str(e),
                )
            
            raise

# Made with Bob