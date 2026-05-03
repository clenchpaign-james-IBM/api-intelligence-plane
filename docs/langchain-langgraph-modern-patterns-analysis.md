# LangChain & LangGraph Modern Patterns Analysis (2024-2026)

**Date**: 2026-04-30  
**Purpose**: Analysis of modern multi-agent workflow patterns for Feature 001-agentic-query

## Executive Summary

Based on research of LangChain 0.3+ and LangGraph 1.1+, the modern approach for building agentic systems has evolved significantly:

1. **AgentExecutor is deprecated** - No longer the recommended pattern
2. **LangGraph StateGraph** - The modern replacement for agent orchestration
3. **Tool Calling via LLM.bind_tools()** - Native LLM tool calling replaces manual parsing
4. **Compiled Graphs** - Agents are now compiled state machines, not executors

## Modern Architecture Pattern

### 1. LangGraph StateGraph (Recommended)

**Pattern**: Define agents as state machines using LangGraph's StateGraph

```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, Annotated, Sequence
import operator

# Define state schema
class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    
# Create graph
workflow = StateGraph(AgentState)

# Define agent node
def agent_node(state: AgentState):
    # LLM with bound tools automatically handles tool calling
    llm_with_tools = llm.bind_tools(tools)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Define tool execution node
def tool_node(state: AgentState):
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls
    
    # Execute tools
    tool_messages = []
    for tool_call in tool_calls:
        tool = tool_map[tool_call["name"]]
        result = tool.invoke(tool_call["args"])
        tool_messages.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": tool_messages}

# Build graph
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")

# Conditional routing
def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    END: END
})
workflow.add_edge("tools", "agent")

# Compile
app = workflow.compile()

# Execute
result = await app.ainvoke({"messages": [HumanMessage(content="query")]})
```

**Key Benefits**:
- ✅ Native tool calling (no manual parsing)
- ✅ Explicit state management
- ✅ Visual graph representation
- ✅ Streaming support
- ✅ Checkpointing for long-running workflows

### 2. Multi-Agent Coordination Pattern

**Pattern**: Coordinator agent delegates to specialized agents

```python
from langgraph.graph import StateGraph, END

class MultiAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
    
# Coordinator decides which agent to invoke
def coordinator_node(state: MultiAgentState):
    llm_with_tools = coordinator_llm.bind_tools([
        select_discovery_agent,
        select_metrics_agent,
        select_security_agent
    ])
    response = llm_with_tools.invoke(state["messages"])
    
    # Extract which agent to call
    if response.tool_calls:
        next_agent = response.tool_calls[0]["name"]
        return {"next_agent": next_agent, "messages": [response]}
    
    return {"messages": [response]}

# Specialized agent nodes
def discovery_agent_node(state: MultiAgentState):
    discovery_llm_with_tools = discovery_llm.bind_tools(discovery_tools)
    response = discovery_llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Build multi-agent graph
workflow = StateGraph(MultiAgentState)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("discovery", discovery_agent_node)
workflow.add_node("metrics", metrics_agent_node)
workflow.add_node("tools", tool_execution_node)

workflow.set_entry_point("coordinator")

# Route based on coordinator decision
def route_to_agent(state: MultiAgentState):
    return state.get("next_agent", END)

workflow.add_conditional_edges("coordinator", route_to_agent, {
    "discovery": "discovery",
    "metrics": "metrics",
    END: END
})

# Each agent can use tools
workflow.add_conditional_edges("discovery", should_use_tools, {
    "tools": "tools",
    "coordinator": "coordinator"
})

app = workflow.compile()
```

### 3. Tool Calling Pattern (Modern)

**Pattern**: Use LLM.bind_tools() for automatic tool invocation

```python
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage

# Define tools using decorator
@tool
def get_api_details(api_id: str) -> dict:
    """Get details for a specific API."""
    return {"api_id": api_id, "name": "Example API"}

# Bind tools to LLM
llm_with_tools = llm.bind_tools([get_api_details])

# LLM automatically decides when to call tools
response = await llm_with_tools.ainvoke([
    HumanMessage(content="Get details for API abc-123")
])

# Response contains tool_calls attribute
if response.tool_calls:
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        # Execute tool
        result = tools_map[tool_name].invoke(tool_args)
```

## Comparison: Old vs New

| Aspect | Old (AgentExecutor) | New (LangGraph) |
|--------|---------------------|-----------------|
| **Orchestration** | AgentExecutor | StateGraph |
| **Tool Calling** | Manual parsing | LLM.bind_tools() |
| **State** | Implicit | Explicit TypedDict |
| **Routing** | Fixed | Conditional edges |
| **Streaming** | Limited | Full support |
| **Visualization** | None | Graph visualization |
| **Checkpointing** | None | Built-in |
| **Multi-Agent** | Complex | Native support |

## Recommended Implementation for Feature 001

### Architecture

```
User Query
    ↓
CoordinatorAgent (StateGraph)
    ↓
[Conditional Routing]
    ↓
├─→ DiscoveryAgent (StateGraph with tools)
├─→ MetricsAgent (StateGraph with tools)
├─→ SecurityAgent (StateGraph with tools)
├─→ ComplianceAgent (StateGraph with tools)
├─→ OptimizationAgent (StateGraph with tools)
└─→ PredictionAgent (StateGraph with tools)
    ↓
Result Synthesis
    ↓
Response
```

### Implementation Steps

1. **Create Base Agent Pattern**
   ```python
   class BaseQueryAgent:
       def __init__(self, llm, tools):
           self.llm = llm
           self.tools = tools
           self.graph = self._build_graph()
       
       def _build_graph(self):
           workflow = StateGraph(AgentState)
           workflow.add_node("agent", self._agent_node)
           workflow.add_node("tools", self._tool_node)
           # ... add edges
           return workflow.compile()
       
       async def execute(self, query: str):
           return await self.graph.ainvoke({
               "messages": [HumanMessage(content=query)]
           })
   ```

2. **Implement Specialized Agents**
   - Each agent extends BaseQueryAgent
   - Each has domain-specific tools
   - Each uses LLM.bind_tools() for automatic tool calling

3. **Create Coordinator**
   ```python
   class CoordinatorAgent:
       def __init__(self, llm, specialized_agents):
           self.llm = llm
           self.agents = specialized_agents
           self.graph = self._build_coordinator_graph()
       
       def _build_coordinator_graph(self):
           workflow = StateGraph(CoordinatorState)
           workflow.add_node("analyze", self._analyze_query)
           workflow.add_node("route", self._route_to_agents)
           workflow.add_node("synthesize", self._synthesize_results)
           # ... add conditional edges
           return workflow.compile()
   ```

## Key Differences from Research Document

The research document (research.md) was written before LangGraph 1.1+ and uses outdated patterns:

1. **Research says**: Use `create_react_agent` from langchain.agents
   **Reality**: This is deprecated, use StateGraph instead

2. **Research says**: Use AgentExecutor
   **Reality**: AgentExecutor is deprecated, use compiled StateGraph

3. **Research says**: Manual tool invocation tracking
   **Reality**: LangGraph handles this automatically via state

## Migration Path

### Phase 1: Update Base Infrastructure
- Replace AgentExecutor references with StateGraph
- Update tool definitions to use @tool decorator
- Implement state schemas using TypedDict

### Phase 2: Implement Agents
- Create BaseQueryAgent with StateGraph
- Implement specialized agents (Discovery, Metrics, etc.)
- Use LLM.bind_tools() for automatic tool calling

### Phase 3: Coordinator
- Build CoordinatorAgent with multi-agent routing
- Implement conditional edges for agent selection
- Add result synthesis node

### Phase 4: Integration
- Wire up to FastAPI endpoints
- Add fallback mechanism
- Implement context management

## Code Example: Modern Discovery Agent

```python
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from typing import TypedDict, Annotated, Sequence
import operator

class DiscoveryAgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage | ToolMessage], operator.add]

@tool
def list_apis() -> list:
    """List all APIs in the system."""
    return [{"id": "1", "name": "API 1"}]

@tool
def get_api_details(api_id: str) -> dict:
    """Get details for a specific API."""
    return {"id": api_id, "name": "API Details"}

class DiscoveryAgent:
    def __init__(self, llm):
        self.llm = llm
        self.tools = [list_apis, get_api_details]
        self.llm_with_tools = llm.bind_tools(self.tools)
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(DiscoveryAgentState)
        
        # Agent node: LLM decides what to do
        def agent_node(state: DiscoveryAgentState):
            response = self.llm_with_tools.invoke(state["messages"])
            return {"messages": [response]}
        
        # Tool node: Execute tools
        def tool_node(state: DiscoveryAgentState):
            last_message = state["messages"][-1]
            tool_messages = []
            
            for tool_call in last_message.tool_calls:
                tool = next(t for t in self.tools if t.name == tool_call["name"])
                result = tool.invoke(tool_call["args"])
                tool_messages.append(ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"]
                ))
            
            return {"messages": tool_messages}
        
        # Build graph
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        
        # Conditional routing
        def should_continue(state: DiscoveryAgentState):
            last_message = state["messages"][-1]
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END
        
        workflow.add_conditional_edges("agent", should_continue, {
            "tools": "tools",
            END: END
        })
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def execute(self, query: str):
        result = await self.graph.ainvoke({
            "messages": [HumanMessage(content=query)]
        })
        return result["messages"][-1].content
```

## Conclusion

The modern LangChain/LangGraph approach is fundamentally different from the research document's recommendations:

1. **Use StateGraph, not AgentExecutor**
2. **Use LLM.bind_tools(), not manual tool parsing**
3. **Use compiled graphs, not executors**
4. **Use conditional edges for routing, not fixed workflows**

This provides:
- Better control flow
- Explicit state management
- Native streaming support
- Built-in checkpointing
- Visual graph representation
- Easier debugging

## References

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- LangChain 0.3 Migration Guide
- StateGraph API Reference
- Tool Calling Guide

---

**Status**: ✅ Analysis Complete  
**Next Step**: Implement agents using StateGraph pattern  
**Last Updated**: 2026-04-30