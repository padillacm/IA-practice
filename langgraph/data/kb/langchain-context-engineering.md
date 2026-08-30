<!-- Fuente: https://github.com/langchain-ai/docs — documentación oficial de LangChain/LangGraph, licencia MIT, (c) 2025 LangChain.
     Extracto reformateado para uso didáctico en el corpus RAG de este curso. -->

# Ingeniería de contexto

> Página original: `langchain/context-engineering.mdx`

## Overview

The hard part of building agents (or any LLM application) is making them reliable enough. While they may work for a prototype, they often fail in real-world use cases.

### Why do agents fail?

When agents fail, it's usually because the LLM call inside the agent took the wrong action / didn't do what we expected. LLMs fail for one of two reasons:

1. The underlying LLM is not capable enough
2. The "right" context was not passed to the LLM

More often than not - it's actually the second reason that causes agents to not be reliable.

**Context engineering** is providing the right information and tools in the right format so the LLM can accomplish a task. This is the number one job of AI Engineers. This lack of "right" context is the number one blocker for more reliable agents, and LangChain's agent abstractions are uniquely designed to facilitate context engineering.

New to context engineering? Start with the [conceptual overview](/oss/concepts/context) to understand the different types of context and when to use them.

### The agent loop

A typical agent loop consists of two main steps:

1. **Model call** - calls the LLM with a prompt and available tools, returns either a response or a request to execute tools
2. **Tool execution** - executes the tools that the LLM requested, returns tool results

<div style={{ display: "flex", justifyContent: "center" }}>
  <img
    src="/oss/images/core_agent_loop.png"
    alt="Core agent loop diagram"
    className="rounded-lg"
  />
</div>

This loop continues until the LLM decides to finish.

### What you can control

To build reliable agents, you need to control what happens at each step of the agent loop, as well as what happens between steps.

| Context Type | What You Control | Transient or Persistent |
|--------------|------------------|-------------------------|
| **[Model Context](#model-context)** | What goes into model calls (instructions, message history, tools, response format) | Transient |
| **[Tool Context](#tool-context)** | What tools can access and produce (reads/writes to state, store, runtime context) | Persistent |
| **[Life-cycle Context](#life-cycle-context)** | What happens between model and tool calls (summarization, guardrails, logging, etc.) | Persistent |

  
    What the LLM sees for a single call. You can modify messages, tools, or prompts without changing what's saved in state.
  
  
    What gets saved in state across turns. Life-cycle hooks and tool writes modify this permanently.
  

### Data sources

Throughout this process, your agent accesses (reads / writes) different sources of data:

| Data Source | Also Known As | Scope | Examples |
|-------------|---------------|-------|----------|
| **Runtime Context** | Static configuration | Conversation-scoped | User ID, API keys, database connections, permissions, environment settings |
| **State** | Short-term memory | Conversation-scoped | Current messages, uploaded files, authentication status, tool results |
| **Store** | Long-term memory | Cross-conversation | User preferences, extracted insights, memories, historical data |

### How it works

LangChain [middleware](/oss/langchain/middleware) is the mechanism under the hood that makes context engineering practical for developers using LangChain.

Middleware allows you to hook into any step in the agent lifecycle and:

* Update context
* Jump to a different step in the agent lifecycle

Throughout this guide, you'll see frequent use of the middleware API as a means to the context engineering end.

## Model context

Control what goes into each model call - instructions, available tools, which model to use, and output format. These decisions directly impact reliability and cost.

    
        Base instructions from the developer to the LLM.
    
    
        The full list of messages (conversation history) sent to the LLM.
    
    
        Utilities the agent has access to for taking actions.
    
    
        The actual model (including configuration) to be called.
    
    
        Schema specification for the model's final response.
    

All of these types of model context can draw from **state** (short-term memory), **store** (long-term memory), or **runtime context** (static configuration).

### System Prompt

The system prompt sets the LLM's behavior and capabilities. Different users, contexts, or conversation stages need different instructions. Successful agents draw on memories, preferences, and configuration to provide the right instructions for the current state of the conversation.

  
    Access message count or conversation context from state:

    

    ```python
    from langchain.agents import create_agent
    from langchain.agents.middleware import dynamic_prompt, ModelRequest

    @dynamic_prompt
    def state_aware_prompt(request: ModelRequest) -> str:
        # request.messages is a shortcut for request.state["messages"]
        message_count = len(request.messages)

        base = "You are a helpful assistant."

        if message_count > 10:
            base += "\nThis is a long conversation - be extra concise."

        return base

    agent = create_agent(
        model="gpt-5.5",
        tools=[...],
        middleware=[state_aware_prompt]
    )
    ```
    :::

    python
- Return a `ExtendedModelResponse` with a `Command` from `wrap_model_call` to inject state updates from the model call layer.
- Use life-cycle hooks like `before_model`, `after_model`, or `wrap_tool_call` (for tool returns) to update the conversation history. See the [middleware documentation](/oss/langchain/middleware) for more details.

See [State updates](/oss/langchain/middleware/custom#state-updates) for more information.

### Tools

Tools let the model interact with databases, APIs, and external systems. How you define and select tools directly impacts whether the model can complete tasks effectively.

#### Defining tools

Each tool needs a clear name, description, argument names, and argument descriptions. These aren't just metadata—they guide the model's reasoning about when and how to use the tool.

```python
from langchain.tools import tool

@tool(parse_docstring=True)
def search_orders(
    user_id: str,
    status: str,
    limit: int = 10
) -> str:
    """Search for user orders by status.

    Use this when the user asks about order history or wants to check
    order status. Always filter by the provided status.

    Args:
        user_id: Unique identifier for the user
        status: Order status: 'pending', 'shipped', or 'delivered'
        limit: Maximum number of results to return
    """
    # Implementation here
    pass
```

#### Selecting tools

Not every tool is appropriate for every situation. Too many tools may overwhelm the model (overload context) and increase errors; too few limit capabilities. Dynamic tool selection adapts the available toolset based on authentication state, user permissions, feature flags, or conversation stage.

  
    Enable advanced tools only after certain conversation milestones:

    

    ```python
    from langchain.agents import create_agent
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from typing import Callable

    @wrap_model_call
    def state_based_tools(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        """Filter tools based on conversation State."""
        # Read from State: check if user has authenticated
        state = request.state  # 
        is_authenticated = state.get("authenticated", False)  # 
        message_count = len(state["messages"])

        # Only enable sensitive tools after authentication
        if not is_authenticated:
            tools = [t for t in request.tools if t.name.startswith("public_")]
            request = request.override(tools=tools)  # 
        elif message_count < 5:
            # Limit tools early in conversation
            tools = [t for t in request.tools if t.name != "advanced_search"]
            request = request.override(tools=tools)  # 

        return handler(request)

    agent = create_agent(
        model="gpt-5.5",
        tools=[public_search, private_search, advanced_search],
        middleware=[state_based_tools]
    )
    ```
    :::

    python
```python
from pydantic import BaseModel, Field

class CustomerSupportTicket(BaseModel):
    """Structured ticket information extracted from customer message."""

    category: str = Field(
        description="Issue category: 'billing', 'technical', 'account', or 'product'"
    )
    priority: str = Field(
        description="Urgency level: 'low', 'medium', 'high', or 'critical'"
    )
    summary: str = Field(
        description="One-sentence summary of the customer's issue"
    )
    customer_sentiment: str = Field(
        description="Customer's emotional tone: 'frustrated', 'neutral', or 'satisfied'"
    )
```

#### Selecting formats

Dynamic response format selection adapts schemas based on user preferences, conversation stage, or role—returning simple formats early and detailed formats as complexity increases.

  
    Configure structured output based on conversation state:

    

    ```python
    from langchain.agents import create_agent
    from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
    from pydantic import BaseModel, Field
    from typing import Callable

    class SimpleResponse(BaseModel):
        """Simple response for early conversation."""
        answer: str = Field(description="A brief answer")

    class DetailedResponse(BaseModel):
        """Detailed response for established conversation."""
        answer: str = Field(description="A detailed answer")
        reasoning: str = Field(description="Explanation of reasoning")
        confidence: float = Field(description="Confidence score 0-1")

    @wrap_model_call
    def state_based_output(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        """Select output format based on State."""
        # request.messages is a shortcut for request.state["messages"]
        message_count = len(request.messages)  # 

        if message_count < 3:
            # Early conversation - use simple format
            request = request.override(response_format=SimpleResponse)  # 
        else:
            # Established conversation - use detailed format
            request = request.override(response_format=DetailedResponse)  # 

        return handler(request)

    agent = create_agent(
        model="gpt-5.5",
        tools=[...],
        middleware=[state_based_output]
    )
    ```
    :::

    python
```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-5.5",
    tools=[...],
    middleware=[
        SummarizationMiddleware(
            model="gpt-5.4-mini",
            trigger={"tokens": 4000},
            keep=("messages", 20),
        ),
    ],
)
```

When the conversation exceeds the token limit, `SummarizationMiddleware` automatically:
1. Summarizes older messages using a separate LLM call
2. Replaces them with a summary message in State (permanently)
3. Keeps recent messages intact for context

The summarized conversation history is permanently updated - future turns will see the summary instead of the original messages.

For a complete list of built-in middleware, available hooks, and how to create custom middleware, see the [Middleware documentation](/oss/langchain/middleware).

## Best practices

1. **Start simple** - Begin with static prompts and tools, add dynamics only when needed
2. **Test incrementally** - Add one context engineering feature at a time
3. **Monitor performance** - Track model calls, token usage, and latency
4. **Use built-in middleware** - Leverage [`SummarizationMiddleware`](/oss/langchain/middleware#summarization), [`LLMToolSelectorMiddleware`](/oss/langchain/middleware#llm-tool-selector), etc.
5. **Document your context strategy** - Make it clear what context is being passed and why
6. **Understand transient vs persistent**: Model context changes are transient (per-call), while life-cycle context changes persist to state

## Related resources

- [Context conceptual overview](/oss/concepts/context) - Understand context types and when to use them
- [Middleware](/oss/langchain/middleware) - Complete middleware guide
- [Tools](/oss/langchain/tools) - Tool creation and context access
- [Memory](/oss/concepts/memory) - Short-term and long-term memory patterns
- [Agents](/oss/langchain/agents) - Core agent concepts
