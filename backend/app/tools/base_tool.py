"""
Router Tool Abstraction Layer - Base Tool Classes

This module provides the base classes for wrapping backend router methods
as LangChain-compatible tools for direct invocation by agents.

Key Design: Direct router method invocation (not MCP HTTP calls)
- Zero network overhead (same process)
- Type safety preserved
- Validation logic maintained
- Sub-millisecond invocation latency

Feature: 001-agentic-query
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC
from typing import Any, Callable, Dict, Optional, Type

from langchain.tools import BaseTool
from pydantic import BaseModel, Field, ValidationError

from app.utils.logging import get_logger

logger = get_logger(__name__)


# Tool result cache (T086)
_tool_cache: Dict[str, tuple[Any, float]] = {}
_tool_cache_ttl = 60  # 60 seconds default TTL
_tool_cache_max_size = 500

# Retry configuration (T089)
_max_retries = 3
_initial_retry_delay = 1.0  # seconds
_max_retry_delay = 10.0  # seconds
_retry_backoff_factor = 2.0


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""

    pass


class RouterToolInput(BaseModel):
    """
    Base input schema for router tools.
    
    Subclasses should define specific parameters for each tool.
    """

    pass


class RouterTool(BaseTool, ABC):
    """
    Base class for wrapping router methods as LangChain tools.
    
    This class provides a standardized interface for invoking backend
    router methods directly from agents, with parameter validation,
    error handling, and invocation logging.
    
    Attributes:
        name: Tool name (must be unique)
        description: Tool description for LLM understanding
        router_method: The backend router method to invoke
        args_schema: Pydantic model defining tool parameters
    """

    name: str
    description: str
    router_method: Callable
    args_schema: Type[BaseModel] = RouterToolInput
    
    # LangChain BaseTool configuration
    return_direct: bool = False
    verbose: bool = False

    def _generate_cache_key(self, **kwargs: Any) -> str:
        """
        Generate cache key for tool invocation (T086).
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Cache key string
        """
        # Create deterministic key from tool name and parameters
        params_str = json.dumps(kwargs, sort_keys=True)
        key_string = f"{self.name}:{params_str}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _get_cached_result(self, **kwargs: Any) -> Optional[Dict[str, Any]]:
        """
        Get cached result if available and not expired (T086).
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Cached result or None
        """
        cache_key = self._generate_cache_key(**kwargs)
        
        if cache_key not in _tool_cache:
            return None
        
        result, timestamp = _tool_cache[cache_key]
        
        # Check if expired
        if time.time() - timestamp > _tool_cache_ttl:
            del _tool_cache[cache_key]
            return None
        
        logger.debug(
            f"Tool cache hit for {self.name}",
            extra={"tool_name": self.name, "cache_key": cache_key}
        )
        
        return result
    
    def _cache_result(self, result: Dict[str, Any], **kwargs: Any) -> None:
        """
        Cache tool result (T086).
        
        Args:
            result: Result to cache
            **kwargs: Tool parameters
        """
        global _tool_cache
        
        # Evict oldest if cache is full
        if len(_tool_cache) >= _tool_cache_max_size:
            oldest_key = min(_tool_cache.keys(), key=lambda k: _tool_cache[k][1])
            del _tool_cache[oldest_key]
        
        cache_key = self._generate_cache_key(**kwargs)
        _tool_cache[cache_key] = (result, time.time())
        
        logger.debug(
            f"Cached result for {self.name}",
            extra={"tool_name": self.name, "cache_size": len(_tool_cache)}
        )
    
    async def _execute_with_retry(
        self,
        validated_input: BaseModel,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Execute router method with exponential backoff retry logic (T089).
        
        Args:
            validated_input: Validated input parameters
            retry_count: Current retry attempt
            
        Returns:
            Router method result
            
        Raises:
            ToolExecutionError: If all retries fail
        """
        try:
            return await self._invoke_router_method(validated_input)
        except Exception as e:
            if retry_count >= _max_retries:
                logger.error(
                    f"Tool {self.name} failed after {retry_count} retries",
                    extra={
                        "tool_name": self.name,
                        "retry_count": retry_count,
                        "error": str(e),
                    }
                )
                raise
            
            # Calculate exponential backoff delay
            delay = min(
                _initial_retry_delay * (_retry_backoff_factor ** retry_count),
                _max_retry_delay
            )
            
            logger.warning(
                f"Tool {self.name} failed, retrying in {delay:.1f}s (attempt {retry_count + 1}/{_max_retries})",
                extra={
                    "tool_name": self.name,
                    "retry_count": retry_count,
                    "delay_seconds": delay,
                    "error": str(e),
                }
            )
            
            await asyncio.sleep(delay)
            return await self._execute_with_retry(validated_input, retry_count + 1)
    
    async def _arun(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute the router method asynchronously.
        
        This is the main execution path for tool invocation. It:
        1. Checks cache for recent results (T086)
        2. Validates parameters against the tool's schema
        3. Calls the router method with retry logic (T089)
        4. Handles errors gracefully
        5. Logs the invocation for observability
        6. Caches the result (T086)
        7. Returns the result
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Dict containing the tool execution result
            
        Raises:
            ToolExecutionError: If validation or execution fails
        """
        # Check cache first (T086)
        cached_result = self._get_cached_result(**kwargs)
        if cached_result is not None:
            return cached_result
        
        start_time = time.time()
        
        try:
            # Validate parameters against schema
            validated_input = self.args_schema(**kwargs)
            
            logger.info(
                f"Tool {self.name} invoked",
                extra={
                    "tool_name": self.name,
                    "parameters": kwargs,
                }
            )
            
            # Call router method with retry logic (T089)
            result = await self._execute_with_retry(validated_input)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Tool {self.name} completed successfully",
                extra={
                    "tool_name": self.name,
                    "execution_time_ms": execution_time_ms,
                }
            )
            
            # Cache the result (T086)
            self._cache_result(result, **kwargs)
            
            return result
            
        except ValidationError as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Tool {self.name} validation failed",
                extra={
                    "tool_name": self.name,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                }
            )
            raise ToolExecutionError(f"Invalid parameters: {e}")
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Tool {self.name} execution failed",
                extra={
                    "tool_name": self.name,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                },
                exc_info=True
            )
            raise ToolExecutionError(f"Execution failed: {e}")

    async def _invoke_router_method(
        self,
        validated_input: BaseModel
    ) -> Dict[str, Any]:
        """
        Invoke the router method with validated parameters.
        
        This method handles the actual invocation of the backend router
        method. Subclasses can override this to customize invocation logic.
        
        Args:
            validated_input: Validated input parameters
            
        Returns:
            Dict containing the router method result
        """
        # Convert Pydantic model to dict for router method
        # NOTE: Do NOT use exclude_none=True because router methods expect
        # all parameters (even if None) since FastAPI Query defaults are
        # already extracted during tool schema creation
        params = validated_input.model_dump()
        
        # Invoke router method directly
        result = await self.router_method(**params)
        
        # Ensure result is a dict
        if not isinstance(result, dict):
            # If result is a Pydantic model, convert to dict
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            elif hasattr(result, "dict"):
                result = result.dict()
            else:
                # Wrap non-dict results
                result = {"result": result}
        
        return result

    def _run(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Synchronous execution - not supported.
        
        All router methods are async, so sync execution is not available.
        """
        raise NotImplementedError(
            f"Tool {self.name} only supports async execution. "
            "Use _arun() instead."
        )


class ToolParameter(BaseModel):
    """
    Metadata for a tool parameter.
    
    Used by the tool registry for auto-discovery and documentation.
    """

    name: str = Field(description="Parameter name")
    type: str = Field(description="Parameter type (string, integer, etc.)")
    required: bool = Field(default=False, description="Whether parameter is required")
    description: str = Field(default="", description="Parameter description")
    default: Optional[Any] = Field(default=None, description="Default value")
    enum: Optional[list] = Field(default=None, description="Allowed values")


class ToolMetadata(BaseModel):
    """
    Metadata for a router tool.
    
    Used by the tool registry for cataloging and discovery.
    """

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    router_method: str = Field(description="Router method path")
    agent_domains: list[str] = Field(
        default_factory=list,
        description="Agent domains that can use this tool"
    )
    parameters: list[ToolParameter] = Field(
        default_factory=list,
        description="Tool parameters"
    )
    returns: Dict[str, Any] = Field(
        default_factory=dict,
        description="Return value schema"
    )
    example: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Example usage"
    )

# Made with Bob
