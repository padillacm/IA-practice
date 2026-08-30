<!-- Fuente: https://github.com/langchain-ai/docs — documentación oficial de LangChain/LangGraph, licencia MIT, (c) 2025 LangChain.
     Extracto reformateado para uso didáctico en el corpus RAG de este curso. -->

# Agentes con create_agent

> Página original: `langchain/agents.mdx`

import AgentInvocationThreadAndContextJs from '/snippets/code-samples/agent-invocation-thread-and-context-js.mdx';
import AgentInvocationThreadAndContextPy from '/snippets/code-samples/agent-invocation-thread-and-context-py.mdx';
import AgentInvocationThreadIdJs from '/snippets/code-samples/agent-invocation-thread-id-js.mdx';
import AgentInvocationThreadIdPy from '/snippets/code-samples/agent-invocation-thread-id-py.mdx';
import AgentsAgentStateJs from '/snippets/code-samples/agents-agent-state-js.mdx';
import AgentsAgentStatePy from '/snippets/code-samples/agents-agent-state-py.mdx';
import AgentsContextManagementJs from '/snippets/code-samples/agents-context-management-js.mdx';
import AgentsContextManagementPy from '/snippets/code-samples/agents-context-management-py.mdx';
import AgentsExecutionEnvironmentJs from '/snippets/code-samples/agents-execution-environment-js.mdx';
import AgentsExecutionEnvironmentPy from '/snippets/code-samples/agents-execution-environment-py.mdx';
import AgentsFaultToleranceJs from '/snippets/code-samples/agents-fault-tolerance-js.mdx';
import AgentsFaultTolerancePy from '/snippets/code-samples/agents-fault-tolerance-py.mdx';
import AgentsGuardrailsJs from '/snippets/code-samples/agents-guardrails-js.mdx';
import AgentsGuardrailsPy from '/snippets/code-samples/agents-guardrails-py.mdx';
import AgentsIntroJs from '/snippets/code-samples/agents-intro-js.mdx';
import AgentsIntroPy from '/snippets/code-samples/agents-intro-py.mdx';
import AgentsModelJs from '/snippets/code-samples/agents-model-js.mdx';
import AgentsModelPy from '/snippets/code-samples/agents-model-py.mdx';
import AgentsNameJs from '/snippets/code-samples/agents-name-js.mdx';
import AgentsNamePy from '/snippets/code-samples/agents-name-py.mdx';
import AgentsPlanningDelegationJs from '/snippets/code-samples/agents-planning-delegation-js.mdx';
import AgentsPlanningDelegationPy from '/snippets/code-samples/agents-planning-delegation-py.mdx';
import AgentsSteeringJs from '/snippets/code-samples/agents-steering-js.mdx';
import AgentsSteeringPy from '/snippets/code-samples/agents-steering-py.mdx';
import AgentsStreamingProgressJs from '/snippets/code-samples/agents-streaming-progress-js.mdx';
import AgentsStreamingProgressPy from '/snippets/code-samples/agents-streaming-progress-py.mdx';
import AgentsStructuredOutputJs from '/snippets/code-samples/agents-structured-output-js.mdx';
import AgentsStructuredOutputPy from '/snippets/code-samples/agents-structured-output-py.mdx';
import AgentsSystemPromptJs from '/snippets/code-samples/agents-system-prompt-js.mdx';
import AgentsSystemPromptPy from '/snippets/code-samples/agents-system-prompt-py.mdx';
import AgentsToolsJs from '/snippets/code-samples/agents-tools-js.mdx';
import AgentsToolsPy from '/snippets/code-samples/agents-tools-py.mdx';

An agent is a model calling tools in a loop until a given task is complete.

<img
    src="/oss/images/core_agent_loop.svg"
    alt="Core agent loop diagram"
    style={{height: "300px", width: "auto", justifyContent: "center"}}
    className="rounded-lg block mx-auto"
/>

A harness is everything around that loop: the prompt, the tools, and any middleware that shapes the model's behavior.

**Agent = Model + Harness**

The job of a harness: get the model the right context at the right time for the given task.

`create_agent` is a highly configurable harness. At its simplest, you can create one with:

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    
    agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools)
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    
    agent = create_agent(model="openai:gpt-5.5", tools=tools)
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    
    agent = create_agent(model="anthropic:claude-sonnet-4-6", tools=tools)
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    
    agent = create_agent(model="openrouter:z-ai/glm-5.2", tools=tools)
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    
    agent = create_agent(model="fireworks:accounts/fireworks/models/glm-5p2", tools=tools)
    ```

    ```python Baseten
    from langchain.agents import create_agent
    
    agent = create_agent(model="baseten:zai-org/GLM-5.2", tools=tools)
    ```

    ```python Ollama
    from langchain.agents import create_agent
    
    agent = create_agent(model="ollama:north-mini-code-1.0", tools=tools)
    ```
</CodeGroup>

Building on that, you can configure the basics directly with the `model=`, `tools=`, and `system_prompt=` parameters. For more advanced capabilities, extend the harness with [middleware](#configure-the-harness).

[Deep Agents](/oss/deepagents/overview) builds on `create_agent` and comes with commonly useful capabilities already assembled, such as planning, file system tools, subagents, and memory. Use `create_agent` when you need to configure the harness yourself.

## Core components

<img
    src="/oss/images/agent_model_harness.svg"
    alt="Agent model and harness components diagram"
    style={{height: "280px", width: "auto", justifyContent: "center"}}
    className="rounded-lg block mx-auto"
/>

### Model

Pass a model identifier string (`"provider:model"`) or an initialized model instance to select the model for your agent. See [Models](/oss/langchain/models) for parameters, provider setup, and dynamic model selection.

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    
    agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools)
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    
    agent = create_agent(model="openai:gpt-5.5", tools=tools)
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    
    agent = create_agent(model="anthropic:claude-sonnet-4-6", tools=tools)
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    
    agent = create_agent(model="openrouter:z-ai/glm-5.2", tools=tools)
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    
    agent = create_agent(model="fireworks:accounts/fireworks/models/glm-5p2", tools=tools)
    ```

    ```python Baseten
    from langchain.agents import create_agent
    
    agent = create_agent(model="baseten:zai-org/GLM-5.2", tools=tools)
    ```

    ```python Ollama
    from langchain.agents import create_agent
    
    agent = create_agent(model="ollama:north-mini-code-1.0", tools=tools)
    ```
</CodeGroup>

### Tools

To provide the agent with tools, pass any Python callable, LangChain tool, or tool dict. See [Tools](/oss/langchain/tools) for tool definition, context access, and dynamic tool selection.

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="google_genai:gemini-3.6-flash", tools=[search])
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="openai:gpt-5.5", tools=[search])
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="anthropic:claude-sonnet-4-6", tools=[search])
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="openrouter:z-ai/glm-5.2", tools=[search])
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="fireworks:accounts/fireworks/models/glm-5p2", tools=[search])
    ```

    ```python Baseten
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="baseten:zai-org/GLM-5.2", tools=[search])
    ```

    ```python Ollama
    from langchain.agents import create_agent
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for information."""
        return f"Results for: {query}"
    
    
    agent = create_agent(model="ollama:north-mini-code-1.0", tools=[search])
    ```
</CodeGroup>

### System prompt

Shape how the agent approaches tasks. The system prompt parameter accepts a string or `SystemMessage`. For dynamic prompts at runtime, use [middleware](/oss/langchain/middleware).

<CodeGroup>
    ```python Google
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```

    ```python OpenAI
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```

    ```python Anthropic
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```

    ```python OpenRouter
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```

    ```python Fireworks
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```

    ```python Baseten
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```

    ```python Ollama
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=tools,
        system_prompt="You are a helpful assistant. Be concise and accurate.",
    )
    ```
</CodeGroup>

### Structured output

Return a validated schema from the agent using `response_format=`. See [Structured output](/oss/langchain/structured-output) for strategies and examples.

<CodeGroup>
    ```python Google
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```

    ```python OpenAI
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="openai:gpt-5.5", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```

    ```python Anthropic
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="anthropic:claude-sonnet-4-6", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```

    ```python OpenRouter
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="openrouter:z-ai/glm-5.2", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```

    ```python Fireworks
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="fireworks:accounts/fireworks/models/glm-5p2", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```

    ```python Baseten
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="baseten:zai-org/GLM-5.2", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```

    ```python Ollama
    from pydantic import BaseModel
    from langchain.agents import create_agent
    
    
    class Answer(BaseModel):
        summary: str
        confidence: float
    
    
    agent = create_agent(model="ollama:north-mini-code-1.0", tools=tools, response_format=Answer)
    result = agent.invoke({"messages": [{"role": "user", "content": "Summarize AI trends"}]})
    result["structured_response"]  # Answer(summary=..., confidence=...)
    ```
</CodeGroup>

### Agent state

Every agent manages its execution context through `AgentState`, a typed dictionary that holds the current conversation history and any custom fields your tools and middleware need.

The built-in field is:

| Field | Type | Description |
|-------|------|-------------|
| `messages` | `list[BaseMessage]` | The full conversation history for the current thread. Append-only: new messages are added, never replaced. |

`AgentState` is also the type signature for every node-style middleware hook (`before_model`, `after_model`, and similar). Hooks receive the current state and can return a dict of updates to merge back into it.

To add custom fields (for example, a `user_id` or a counter), subclass `AgentState` and pass the subclass to `create_agent` via `state_schema=`:

<CodeGroup>
    ```python Google
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[],
        state_schema=MyState,  # 
    )
    ```

    ```python OpenAI
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[],
        state_schema=MyState,  # 
    )
    ```

    ```python Anthropic
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[],
        state_schema=MyState,  # 
    )
    ```

    ```python OpenRouter
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[],
        state_schema=MyState,  # 
    )
    ```

    ```python Fireworks
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[],
        state_schema=MyState,  # 
    )
    ```

    ```python Baseten
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[],
        state_schema=MyState,  # 
    )
    ```

    ```python Ollama
    from langchain.agents import AgentState, create_agent
    
    
    class MyState(AgentState):
        user_id: str
        call_count: int
    
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[],
        state_schema=MyState,  # 
    )
    ```
</CodeGroup>

For full details, examples, and middleware-level state schemas, see [Short-term memory](/oss/langchain/short-term-memory#customizing-agent-memory) and [Custom middleware](/oss/langchain/middleware/custom#state-updates).

## Invocation

Trace each step of this loop, debug tool calls, and evaluate agent outputs with [LangSmith](https://smith.langchain.com). Follow the [tracing quickstart](/langsmith/trace-with-langchain) to get set up. We recommend you also set up [LangSmith Engine](/langsmith/engine) which monitors your traces, detects issues, and proposes fixes.

You can invoke an agent with a message. Behind the scenes that passes an update to the agent's [`State`](/oss/langgraph/graph-api#state). All agents include a [sequence of messages](/oss/langgraph/use-graph-api#messagesstate) in their state; to invoke the agent, pass a new message along with a `thread_id` so the agent can persist and resume conversation history:

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```

    ```python Baseten
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```

    ```python Ollama
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[],
        checkpointer=InMemorySaver(),
    )
    
    config = {"configurable": {"thread_id": str(uuid7())}}
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config=config,
    )
    
    # A follow-up turn on the same conversation: reuse the same thread_id to keep history
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What about tomorrow?"}]},
        config=config,
    )
    ```
</CodeGroup>

Persisting conversation history with `thread_id` requires the agent to be configured with a [checkpointer](/oss/langchain/long-term-memory). When deployed on [LangSmith](/langsmith/deployment), a checkpointer is provisioned automatically. Locally, pass one explicitly, for example `create_agent(..., checkpointer=InMemorySaver())`.

If you also need to pass per-run configuration (such as a user ID, API keys, or feature flags) to tools and middleware, pass it as `context` alongside `config`. Define the shape of that data with `context_schema` and access it through `runtime.context`:

<CodeGroup>
    ```python Google
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```

    ```python OpenAI
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```

    ```python Anthropic
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```

    ```python OpenRouter
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```

    ```python Fireworks
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```

    ```python Baseten
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```

    ```python Ollama
    from dataclasses import dataclass
    
    from langchain.agents import create_agent
    from langchain_core.utils.uuid import uuid7
    from langgraph.checkpoint.memory import InMemorySaver
    
    
    @dataclass
    class Context:
        user_id: str
    
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[],
        context_schema=Context,
        checkpointer=InMemorySaver(),
    )
    
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]},
        config={"configurable": {"thread_id": str(uuid7())}},
        context=Context(user_id="user-123"),
    )
    ```
</CodeGroup>

`thread_id` scopes the *conversation* (message history, checkpoints), while `context` carries *per-run* data your tools and middleware read at invocation time. Both are commonly passed together. See [tool context](/oss/langchain/tools#context) and [Runtime](/oss/langchain/runtime) for more.

## Streaming

`invoke` returns the final response at the end of a run. If an agent executes multiple tool calls, users often need progress updates before completion. Use streaming to surface intermediate messages and tool activity as they happen.

```python
from langchain.messages import AIMessage, HumanMessage

stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "Search for AI news and summarize the findings"}]},
    version="v3",
)
for snapshot in stream.values:
    # Each snapshot contains the full state at that point
    latest_message = snapshot["messages"][-1]
    if latest_message.content:
        if isinstance(latest_message, HumanMessage):
            print(f"User: {latest_message.content}")
        elif isinstance(latest_message, AIMessage):
            print(f"Agent: {latest_message.content}")
    elif latest_message.tool_calls:
        print(f"Calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")
```

For streaming modes, event types, and UI patterns, see [Streaming](/oss/langchain/streaming).

## Configure the harness

`create_agent` is highly extensible. Middleware is the primitive for customization: each piece handles one concern, hooks into the agent loop at the right moment, and composes freely with any other. Take exactly what your use case needs and skip the rest.

Common patterns are prebuilt as first-class middleware. You can build anything else as [custom middleware](/oss/langchain/middleware/custom).

<img
    src="/oss/images/agent_harness_capabilities.svg"
    alt="Agent harness capabilities by category"
    style={{height: "300px", width: "auto", justifyContent: "center"}}
    className="rounded-lg block mx-auto"
/>

As agents take on complex work, they need support across a few key areas. The middleware ecosystem provides:

  
    Tools, filesystem, sandboxes, and code execution
  
  
    Summarization, memory, skills, and prompt caching
  
  
    Todo lists and subagents for parallel, isolated work
  
  
    Retries, fallbacks, and call limits
  
  
    PII detection and content controls
  
  
    Human-in-the-loop approval before high-impact actions
  

`create_deep_agent` pre-assembles this stack for long-running coding and research tasks (filesystem, summarization, subagents, and prompt caching included by default). See [Deep Agents](/oss/deepagents/harness) for the full prebuilt harness.

### Execution environment

Agents are especially useful when they can take action rather than just generate text. The execution environment gives the agent a workspace: tools it can call, a filesystem for reading and writing files across turns, and code execution for running scripts or shell commands.

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```

    ```python Baseten
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```

    ```python Ollama
    from langchain.agents import create_agent
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[search],
        middleware=[FilesystemMiddleware(backend=StateBackend())],
    )
    ```
</CodeGroup>

See `FilesystemMiddleware`, [Sandboxes](/oss/deepagents/sandboxes), [Interpreters](/oss/deepagents/interpreters).

This example imports from the `deepagents` package. Install it with:

<CodeGroup>
  ```bash pip
  pip install deepagents
  ```

  ```bash uv
  uv add deepagents
  ```
</CodeGroup>

### Context management

Every model call has a fixed context window. As an agent runs, that window fills with accumulating history, tool results, and intermediate steps. Summarization compresses history before overflow hits; memory loads persistent instructions at startup so knowledge carries across sessions; skills surface domain knowledge on demand rather than loading everything upfront.

<CodeGroup>
    ```python Google
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "google_genai:gemini-3.6-flash"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```

    ```python OpenAI
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "openai:gpt-5.5"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```

    ```python Anthropic
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "anthropic:claude-sonnet-4-6"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```

    ```python OpenRouter
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "openrouter:z-ai/glm-5.2"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```

    ```python Fireworks
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "fireworks:accounts/fireworks/models/glm-5p2"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```

    ```python Baseten
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "baseten:zai-org/GLM-5.2"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```

    ```python Ollama
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, SummarizationMiddleware
    
    backend = StateBackend()
    model = "ollama:north-mini-code-1.0"
    
    agent = create_agent(
        model=model,
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            SummarizationMiddleware(model=model, backend=backend),
            MemoryMiddleware(backend=backend, sources=["./AGENTS.md"]),
            SkillsMiddleware(backend=backend, sources=["./skills/"]),
        ],
    )
    ```
</CodeGroup>

See `SummarizationMiddleware`, `MemoryMiddleware`, [Skills](/oss/langchain/multi-agent/skills), [Context engineering](/oss/deepagents/context-engineering).

This example imports from the `deepagents` package. Install it with:

<CodeGroup>
  ```bash pip
  pip install deepagents
  ```

  ```bash uv
  uv add deepagents
  ```
</CodeGroup>

### Planning and delegation

Complex tasks often exceed what one context window can handle. Delegation lets the main agent break work into pieces, hand them to subagents that each run in their own isolated context, and stay focused on coordination rather than execution. Work can run in parallel; the main agent's context stays clean.

<CodeGroup>
    ```python Google
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```

    ```python OpenAI
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```

    ```python Anthropic
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```

    ```python OpenRouter
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```

    ```python Fireworks
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```

    ```python Baseten
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```

    ```python Ollama
    from deepagents.backends import StateBackend
    from deepagents.middleware import FilesystemMiddleware
    from deepagents.middleware.subagents import SubAgentMiddleware
    from langchain.agents import create_agent
    from langchain.agents.middleware import TodoListMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    backend = StateBackend()
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[search],
        middleware=[
            FilesystemMiddleware(backend=backend),
            TodoListMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=[
                    {
                        "name": "researcher",
                        "description": "Searches and returns a structured summary.",
                        "system_prompt": "Use the search tool to research the question and summarize key points.",
                        "tools": [search],
                        "model": "anthropic:claude-sonnet-4-6",
                        "middleware": [],
                    }
                ],
            ),
        ],
    )
    ```
</CodeGroup>

See [Subagents](/oss/langchain/multi-agent/subagents).

This example imports from the `deepagents` package. Install it with:

<CodeGroup>
  ```bash pip
  pip install deepagents
  ```

  ```bash uv
  uv add deepagents
  ```
</CodeGroup>

### Name your agent

Optionally use an identifier for the agent. This is especially useful when embedding the agent as a subgraph in [multi-agent](/oss/langchain/multi-agent) systems.

<CodeGroup>
    ```python Google
    agent = create_agent(model="google_genai:gemini-3.6-flash", tools=tools, name="research_assistant")
    ```

    ```python OpenAI
    agent = create_agent(model="openai:gpt-5.5", tools=tools, name="research_assistant")
    ```

    ```python Anthropic
    agent = create_agent(model="anthropic:claude-sonnet-4-6", tools=tools, name="research_assistant")
    ```

    ```python OpenRouter
    agent = create_agent(model="openrouter:z-ai/glm-5.2", tools=tools, name="research_assistant")
    ```

    ```python Fireworks
    agent = create_agent(model="fireworks:accounts/fireworks/models/glm-5p2", tools=tools, name="research_assistant")
    ```

    ```python Baseten
    agent = create_agent(model="baseten:zai-org/GLM-5.2", tools=tools, name="research_assistant")
    ```

    ```python Ollama
    agent = create_agent(model="ollama:north-mini-code-1.0", tools=tools, name="research_assistant")
    ```
</CodeGroup>

### Fault tolerance

Agents in production encounter failures that rarely appear in development: rate limits, model timeouts, transient API errors. Fault tolerance middleware handles these at the infrastructure level so your tools and business logic don't need try/catch around every call.

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```

    ```python Baseten
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```

    ```python Ollama
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[search],
        middleware=[
            ModelRetryMiddleware(max_retries=3),
            ToolRetryMiddleware(max_retries=2),
        ],
    )
    ```
</CodeGroup>

See `ModelRetryMiddleware`, `ToolRetryMiddleware`, [Prebuilt middleware](/oss/langchain/middleware/built-in).

### Guardrails

Some policies can't live in a prompt—they need to be enforced deterministically regardless of what the model does. Guardrails intercept data as it flows through the agent loop, applying compliance rules or content policies before tool results reach the model's context.

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```

    ```python Baseten
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```

    ```python Ollama
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[search],
        middleware=[PIIMiddleware("email")],
    )
    ```
</CodeGroup>

See `PIIMiddleware`, [Prebuilt middleware](/oss/langchain/middleware/built-in).

### Steering

Full autonomy isn't always appropriate. Steering lets you place humans at specific decision points—before destructive writes, expensive API calls, or anything requiring judgment—without restructuring your agent. The agent pauses and waits; a human approves, edits, or rejects; execution continues.

<CodeGroup>
    ```python Google
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="google_genai:gemini-3.6-flash",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```

    ```python OpenAI
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="openai:gpt-5.5",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```

    ```python Anthropic
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```

    ```python OpenRouter
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="openrouter:z-ai/glm-5.2",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```

    ```python Fireworks
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="fireworks:accounts/fireworks/models/glm-5p2",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```

    ```python Baseten
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="baseten:zai-org/GLM-5.2",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```

    ```python Ollama
    from langchain.agents import create_agent
    from langchain.agents.middleware import HumanInTheLoopMiddleware
    from langchain.tools import tool
    
    
    @tool
    def search(query: str) -> str:
        """Search for a query and return a short summary."""
        return f"Search results for: {query}"
    
    
    agent = create_agent(
        model="ollama:north-mini-code-1.0",
        tools=[search],
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"write_file": True})],
    )
    ```
</CodeGroup>

See `HumanInTheLoopMiddleware`, [Human-in-the-loop](/oss/langchain/human-in-the-loop).

### Middleware resources

  
    How the middleware stack works and when hooks fire
  
  
    Full reference with configuration examples
  
  
    Write your own hooks for business logic, PII scrubbing, and more
