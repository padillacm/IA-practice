<!-- Fuente: https://github.com/langchain-ai/docs — documentación oficial de LangChain/LangGraph, licencia MIT, (c) 2025 LangChain.
     Extracto reformateado para uso didáctico en el corpus RAG de este curso. -->

# Subgrafos

> Página original: `langgraph/use-subgraphs.mdx`

import LanggraphSubgraphsInterruptV2Py from '/snippets/code-samples/langgraph-subgraphs-interrupt-v2-py.mdx';

This guide explains the mechanics of using subgraphs. A subgraph is a [graph](/oss/langgraph/graph-api#graphs) that is used as a [node](/oss/langgraph/graph-api#nodes) in another graph.

Subgraphs are useful for:
- Building [multi-agent systems](/oss/langchain/multi-agent)
- Reusing a set of nodes in multiple graphs
- Distributing development: when you want different teams to work on different parts of the graph independently, you can define each part as a subgraph, and as long as the subgraph interface (the input and output schemas) is respected, the parent graph can be built without knowing any details of the subgraph

## Setup

<CodeGroup>
```bash pip
pip install -U langgraph
```

```bash uv
uv add langgraph
```
</CodeGroup>

**Set up LangSmith for LangGraph development**
Sign up for [LangSmith](https://smith.langchain.com) to quickly spot issues and improve the performance of your LangGraph projects. LangSmith lets you use trace data to debug, test, and monitor your LLM apps built with LangGraph—read more about [how to get started with LangSmith](https://docs.smith.langchain.com).

## Define subgraph communication

When adding subgraphs, you need to define how the parent graph and the subgraph communicate:

| Pattern | When to use | State schemas |
|---------|------------|--------------|
| [Call a subgraph inside a node](#call-a-subgraph-inside-a-node) | Parent and subgraph have **different state schemas** (no shared keys), or you need to transform state between them | You write a wrapper function that maps parent state to subgraph input and subgraph output back to parent state |
| [Add a subgraph as a node](#add-a-subgraph-as-a-node) | Parent and subgraph **share state keys**—the subgraph reads from and writes to the same channels as the parent | You pass the compiled subgraph directly to `add_node`—no wrapper function needed |

<a id="invoke-a-graph-from-a-node"></a>
### Call a subgraph inside a node

When the parent graph and subgraph have **different state schemas** (no shared keys), invoke the subgraph inside a node function. This is common when you want to keep a private message history for each agent in a [multi-agent](/oss/langchain/multi-agent) system.

The node function transforms the parent state to the subgraph state before invoking the subgraph, and transforms the results back to the parent state before returning.

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

class SubgraphState(TypedDict):
    bar: str

# Subgraph

def subgraph_node_1(state: SubgraphState):
    return {"bar": "hi! " + state["bar"]}

subgraph_builder = StateGraph(SubgraphState)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# Parent graph

class State(TypedDict):
    foo: str

def call_subgraph(state: State):
    # Transform the state to the subgraph state
    subgraph_output = subgraph.invoke({"bar": state["foo"]})  # 
    # Transform response back to the parent state
    return {"foo": subgraph_output["bar"]}

builder = StateGraph(State)
builder.add_node("node_1", call_subgraph)
builder.add_edge(START, "node_1")
graph = builder.compile()
```

  
  ```python
  from typing_extensions import TypedDict
  from langgraph.graph.state import StateGraph, START

  # Define subgraph
  class SubgraphState(TypedDict):
      # note that none of these keys are shared with the parent graph state
      bar: str
      baz: str

  def subgraph_node_1(state: SubgraphState):
      return {"baz": "baz"}

  def subgraph_node_2(state: SubgraphState):
      return {"bar": state["bar"] + state["baz"]}

  subgraph_builder = StateGraph(SubgraphState)
  subgraph_builder.add_node(subgraph_node_1)
  subgraph_builder.add_node(subgraph_node_2)
  subgraph_builder.add_edge(START, "subgraph_node_1")
  subgraph_builder.add_edge("subgraph_node_1", "subgraph_node_2")
  subgraph = subgraph_builder.compile()

  # Define parent graph
  class ParentState(TypedDict):
      foo: str

  def node_1(state: ParentState):
      return {"foo": "hi! " + state["foo"]}

  def node_2(state: ParentState):
      # Transform the state to the subgraph state
      response = subgraph.invoke({"bar": state["foo"]})
      # Transform response back to the parent state
      return {"foo": response["bar"]}

  builder = StateGraph(ParentState)
  builder.add_node("node_1", node_1)
  builder.add_node("node_2", node_2)
  builder.add_edge(START, "node_1")
  builder.add_edge("node_1", "node_2")
  graph = builder.compile()

  stream = graph.stream_events({"foo": "foo"}, version="v3")
  for event in stream:
      if event["method"] == "updates":
          print(event["params"]["namespace"], event["params"]["data"])
  ```

  ```
  [] {'node_1': {'foo': 'hi! foo'}}
  ['node_2:577b710b-64ae-31fb-9455-6a4d4cc2b0b9'] {'subgraph_node_1': {'baz': 'baz'}}
  ['node_2:577b710b-64ae-31fb-9455-6a4d4cc2b0b9'] {'subgraph_node_2': {'bar': 'hi! foobaz'}}
  [] {'node_2': {'foo': 'hi! foobaz'}}
  ```
  :::

  python
1. Define the subgraph workflow (`subgraph_builder` in the example below) and compile it
2. Pass compiled subgraph to the `add_node` method when defining the parent graph workflow

```python
from typing_extensions import TypedDict
from langgraph.graph.state import StateGraph, START

class State(TypedDict):
    foo: str

# Subgraph

def subgraph_node_1(state: State):
    return {"foo": "hi! " + state["foo"]}

subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

# Parent graph

builder = StateGraph(State)
builder.add_node("node_1", subgraph)  # 
builder.add_edge(START, "node_1")
graph = builder.compile()
```

  
  ```python
  from typing_extensions import TypedDict
  from langgraph.graph.state import StateGraph, START

  # Define subgraph
  class SubgraphState(TypedDict):
      foo: str  # shared with parent graph state
      bar: str  # private to SubgraphState

  def subgraph_node_1(state: SubgraphState):
      return {"bar": "bar"}

  def subgraph_node_2(state: SubgraphState):
      # note that this node is using a state key ('bar') that is only available in the subgraph
      # and is sending update on the shared state key ('foo')
      return {"foo": state["foo"] + state["bar"]}

  subgraph_builder = StateGraph(SubgraphState)
  subgraph_builder.add_node(subgraph_node_1)
  subgraph_builder.add_node(subgraph_node_2)
  subgraph_builder.add_edge(START, "subgraph_node_1")
  subgraph_builder.add_edge("subgraph_node_1", "subgraph_node_2")
  subgraph = subgraph_builder.compile()

  # Define parent graph
  class ParentState(TypedDict):
      foo: str

  def node_1(state: ParentState):
      return {"foo": "hi! " + state["foo"]}

  builder = StateGraph(ParentState)
  builder.add_node("node_1", node_1)
  builder.add_node("node_2", subgraph)
  builder.add_edge(START, "node_1")
  builder.add_edge("node_1", "node_2")
  graph = builder.compile()

  stream = graph.stream_events({"foo": "foo"}, version="v3")
  for event in stream:
      if event["method"] == "updates" and not event["params"]["namespace"]:
          print(event["params"]["data"])
  ```

  ```
  {'node_1': {'foo': 'hi! foo'}}
  {'node_2': {'foo': 'hi! foobar'}}
  ```
  :::

  python

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

@tool
def fruit_info(fruit_name: str) -> str:
    """Look up fruit info."""
    return f"Info about {fruit_name}"

@tool
def veggie_info(veggie_name: str) -> str:
    """Look up veggie info."""
    return f"Info about {veggie_name}"

# Subagents - no checkpointer setting (inherits parent)
fruit_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[fruit_info],
    prompt="You are a fruit expert. Use the fruit_info tool. Respond in one sentence.",
)

veggie_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[veggie_info],
    prompt="You are a veggie expert. Use the veggie_info tool. Respond in one sentence.",
)

# Wrap subagents as tools for the outer agent
@tool
def ask_fruit_expert(question: str) -> str:
    """Ask the fruit expert. Use for ALL fruit questions."""
    response = fruit_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
    )
    return response["messages"][-1].content

@tool
def ask_veggie_expert(question: str) -> str:
    """Ask the veggie expert. Use for ALL veggie questions."""
    response = veggie_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
    )
    return response["messages"][-1].content

# Outer agent with checkpointer
agent = create_agent(
    model="gpt-5.4-mini",
    tools=[ask_fruit_expert, ask_veggie_expert],
    prompt=(
        "You have two experts: ask_fruit_expert and ask_veggie_expert. "
        "ALWAYS delegate questions to the appropriate expert."
    ),
    checkpointer=MemorySaver(),
)
```

  
  Each invocation can use `interrupt()` to pause and resume. Add `interrupt()` to a tool function to require user approval before proceeding:

  ```python
  @tool
  def fruit_info(fruit_name: str) -> str:
      """Look up fruit info."""
      interrupt("continue?")  # 
      return f"Info about {fruit_name}"
  ```

  
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "1"}}

# Stream events - the subagent's tool calls interrupt()
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "Tell me about apples"}]},
    config=config,
    version="v3",
)
output = stream.output  # drive the stream to completion
# stream.interrupts contains pending interrupts (and stream.interrupted is True)

# Resume - approve the interrupt
resumed = agent.stream_events(Command(resume=True), config=config, version="v3")
final = resumed.output
```

  
  
  Each invocation starts with a fresh subagent state. The subagent does not remember previous calls:

  ```python
  config = {"configurable": {"thread_id": "1"}}

  # First call
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Tell me about apples"}]},
      config=config,
  )
  # Subagent message count: 4

  # Second call - subagent starts fresh, no memory of apples
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Now tell me about bananas"}]},
      config=config,
  )
  # Subagent message count: 4 (still fresh!)
  ```
  
  
  Multiple calls to the same subgraph work without conflicts, since each invocation gets its own checkpoint namespace:

  ```python
  config = {"configurable": {"thread_id": "1"}}

  # LLM calls ask_fruit_expert for both apples and bananas
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Tell me about apples and bananas"}]},
      config=config,
  )
  # Subagent message count: 4 (apples - fresh)
  # Subagent message count: 4 (bananas - fresh)
  ```
  

#### Per-thread

Use per-thread persistence when a subagent needs to remember previous interactions. For example, a research assistant that builds up context over several exchanges, or a coding assistant that tracks what files it has already edited. The subagent's conversation history and data accumulate across calls on the same thread. Each call picks up where the last one left off.

Compile with `checkpointer=True` to enable this behavior.

Per-thread subgraphs do not support parallel tool calls. When an LLM has access to a per-thread subagent as a tool, it may try to call that tool multiple times in parallel (for example, asking the fruit expert about apples and bananas simultaneously). This causes checkpoint conflicts because both calls write to the same namespace.

The examples below use LangChain's `ToolCallLimitMiddleware` to prevent this. If you're building with pure LangGraph `StateGraph`, you need to prevent parallel tool calls yourself—for example, by configuring your model to disable parallel tool calling or by adding logic to ensure the same subgraph is not invoked multiple times in parallel.

The following examples use a fruit expert subagent compiled with `checkpointer=True`:

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

@tool
def fruit_info(fruit_name: str) -> str:
    """Look up fruit info."""
    return f"Info about {fruit_name}"

# Subagent with checkpointer=True for persistent state
fruit_agent = create_agent(
    model="gpt-5.4-mini",
    tools=[fruit_info],
    prompt="You are a fruit expert. Use the fruit_info tool. Respond in one sentence.",
    checkpointer=True,  # 
)

# Wrap subagent as a tool for the outer agent
@tool
def ask_fruit_expert(question: str) -> str:
    """Ask the fruit expert. Use for ALL fruit questions."""
    response = fruit_agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
    )
    return response["messages"][-1].content

# Outer agent with checkpointer
# Use ToolCallLimitMiddleware to prevent parallel calls to per-thread subagents,
# which would cause checkpoint conflicts.
agent = create_agent(
    model="gpt-5.4-mini",
    tools=[ask_fruit_expert],
    prompt="You have a fruit expert. ALWAYS delegate fruit questions to ask_fruit_expert.",
    middleware=[  # 
        ToolCallLimitMiddleware(tool_name="ask_fruit_expert", run_limit=1),  # 
    ],  # 
    checkpointer=MemorySaver(),
)
```

  
  Per-thread subagents support `interrupt()` just like per-invocation. Add `interrupt()` to a tool function to require user approval:

  ```python
  @tool
  def fruit_info(fruit_name: str) -> str:
      """Look up fruit info."""
      interrupt("continue?")  # 
      return f"Info about {fruit_name}"
  ```

  
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "1"}}

# Stream events - the subagent's tool calls interrupt()
stream = agent.stream_events(
    {"messages": [{"role": "user", "content": "Tell me about apples"}]},
    config=config,
    version="v3",
)
output = stream.output  # drive the stream to completion
# stream.interrupts contains pending interrupts (and stream.interrupted is True)

# Resume - approve the interrupt
resumed = agent.stream_events(Command(resume=True), config=config, version="v3")
final = resumed.output
```

  
  
  State accumulates across invocations—the subagent remembers past conversations:

  ```python
  config = {"configurable": {"thread_id": "1"}}

  # First call
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Tell me about apples"}]},
      config=config,
  )
  # Subagent message count: 4

  # Second call - subagent REMEMBERS apples conversation
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Now tell me about bananas"}]},
      config=config,
  )
  # Subagent message count: 8 (accumulated!)
  ```
  
  

  When you have multiple **different** per-thread subgraphs (for example, a fruit expert and a veggie expert), each one needs its own storage space so their checkpoints don't overwrite each other. This is called **namespace isolation**.

  If you [call subgraphs inside a node](#call-a-subgraph-inside-a-node), LangGraph assigns namespaces based on call order (first call, second call, etc.). This means reordering your calls can mix up which subgraph loads which state. To avoid this, wrap each subagent in its own `StateGraph` with a unique node name—this gives each subgraph a stable, unique namespace:

  ```python
  from langgraph.graph import MessagesState, StateGraph

  def create_sub_agent(model, *, name, **kwargs):
      """Wrap an agent with a unique node name for namespace isolation."""
      agent = create_agent(model=model, name=name, **kwargs)
      return (
          StateGraph(MessagesState)
          .add_node(name, agent)  # unique name → stable namespace  # 
          .add_edge("__start__", name)
          .compile()
      )

  fruit_agent = create_sub_agent(
      "gpt-5.4-mini", name="fruit_agent",
      tools=[fruit_info], prompt="...", checkpointer=True,
  )
  veggie_agent = create_sub_agent(
      "gpt-5.4-mini", name="veggie_agent",
      tools=[veggie_info], prompt="...", checkpointer=True,
  )

  config = {"configurable": {"thread_id": "1"}}

  # First call - LLM calls both fruit and veggie experts
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Tell me about cherries and broccoli"}]},
      config=config,
  )
  # Fruit subagent message count: 4
  # Veggie subagent message count: 4

  # Second call - both agents accumulate independently
  response = agent.invoke(
      {"messages": [{"role": "user", "content": "Now tell me about oranges and carrots"}]},
      config=config,
  )
  # Fruit subagent message count: 8 (remembers cherries!)
  # Veggie subagent message count: 8 (remembers broccoli!)
  ```

  Subgraphs [added as nodes](#add-a-subgraph-as-a-node) already get name-based namespaces automatically, so they don't need this wrapper.
  

### Stateless

Use this when you want to run a subagent like a plain function call with no checkpointing overhead. The subgraph cannot pause/resume and does not benefit from [durable execution](/oss/langgraph/persistence). Compile with `checkpointer=False`.

Without checkpointing, the subgraph has no durable execution. If the process crashes mid-run, the subgraph cannot recover and must be re-run from the beginning.

```python
subgraph_builder = StateGraph(...)
subgraph = subgraph_builder.compile(checkpointer=False)  # 
```

### Checkpointer reference

Control subgraph persistence with the `checkpointer` parameter on `.compile()`:

```python
subgraph = builder.compile(checkpointer=False)  # or True / None
```

| Feature | Per-invocation (default) | Per-thread | Stateless |
|---|---|---|---|
| `checkpointer=` | `None` | `True` | `False` |
| Interrupts (HITL) | ✅ | ✅ | ❌ |
| Multi-turn memory | ❌ | ✅ | ❌ |
| Multiple calls (different subgraphs) | ✅ | <Tooltip tip="Calls to multiple per-thread subgraphs in the same node can cause namespace conflicts. Workarounds are available.">⚠️</Tooltip> | ✅ |
| Multiple calls (same subgraph) | ✅ | ❌ | ✅ |
| State inspection | <Tooltip tip="State inspection with per-invocation persistence is available for the current invocation only (while interrupted). Each invocation starts fresh, so there is no accumulated state to inspect after the invocation completes.">⚠️</Tooltip> | ✅ | ❌ |

- **Interrupts (HITL)**: The subgraph can use [interrupt()](/oss/langgraph/interrupts) to pause execution and wait for user input, then resume where it left off.
- **Multi-turn memory**: The subgraph retains its state across multiple invocations within the same [thread](/oss/langgraph/checkpointers#threads). Each call picks up where the last one left off rather than starting fresh.
- **Multiple calls (different subgraphs)**: Multiple different subgraph instances can be invoked within a single node without checkpoint namespace conflicts.
- **Multiple calls (same subgraph)**: The same subgraph instance can be invoked multiple times within a single node. With stateful persistence, these calls write to the same checkpoint namespace and conflict—use per-invocation persistence instead.
- **State inspection**: The subgraph's state is available via `get_state(config, subgraphs=True)` for debugging and monitoring.

## View subgraph state

When you enable [persistence](/oss/langgraph/persistence), you can inspect the subgraph state using the subgraphs option. With [stateless](#stateless) checkpointing (`checkpointer=False`), no subgraph checkpoints are saved, so subgraph state is not available.

Viewing subgraph state requires that LangGraph can **statically discover** the subgraph—i.e., it is [added as a node](#add-a-subgraph-as-a-node) or [called inside a node](#call-a-subgraph-inside-a-node). It does not work when a subgraph is called inside a [tool](/oss/langchain/tools) function or other indirection (e.g., the [subagents](/oss/langchain/multi-agent/subagents) pattern). Interrupts still propagate to the top-level graph regardless of nesting.

  
  Returns subgraph state for the **current invocation only**. Each invocation starts fresh.

  ```python
  from langgraph.graph import START, StateGraph
  from langgraph.checkpoint.memory import MemorySaver
  from langgraph.types import interrupt, Command
  from typing_extensions import TypedDict

  class State(TypedDict):
      foo: str

  # Subgraph
  def subgraph_node_1(state: State):
      value = interrupt("Provide value:")
      return {"foo": state["foo"] + value}

  subgraph_builder = StateGraph(State)
  subgraph_builder.add_node(subgraph_node_1)
  subgraph_builder.add_edge(START, "subgraph_node_1")
  subgraph = subgraph_builder.compile()  # inherits parent checkpointer

  # Parent graph
  builder = StateGraph(State)
  builder.add_node("node_1", subgraph)
  builder.add_edge(START, "node_1")

  checkpointer = MemorySaver()
  graph = builder.compile(checkpointer=checkpointer)

  config = {"configurable": {"thread_id": "1"}}

  graph.invoke({"foo": ""}, config)

  # View subgraph state for the current invocation
  subgraph_state = graph.get_state(config, subgraphs=True).tasks[0].state  # 

  # Resume the subgraph
  graph.invoke(Command(resume="bar"), config)
  ```
  
  
  Returns **accumulated** subgraph state across all invocations on this thread.

  ```python
  from langgraph.graph import START, StateGraph, MessagesState
  from langgraph.checkpoint.memory import MemorySaver

  # Subgraph with its own persistent state
  subgraph_builder = StateGraph(MessagesState)
  # ... add nodes and edges
  subgraph = subgraph_builder.compile(checkpointer=True)  # 

  # Parent graph
  builder = StateGraph(MessagesState)
  builder.add_node("agent", subgraph)
  builder.add_edge(START, "agent")

  checkpointer = MemorySaver()
  graph = builder.compile(checkpointer=checkpointer)

  config = {"configurable": {"thread_id": "1"}}

  graph.invoke({"messages": [{"role": "user", "content": "hi"}]}, config)
  graph.invoke({"messages": [{"role": "user", "content": "what did I say?"}]}, config)

  # View accumulated subgraph state (includes messages from both invocations)
  subgraph_state = graph.get_state(config, subgraphs=True).tasks[0].state  # 
  ```
  

## Stream subgraph outputs

To observe nested graph executions, we recommend [event streaming](/oss/langgraph/event-streaming): the `stream.subgraphs` projection discovers each nested run and exposes its `path`, `messages`, and `values` without parsing namespace strings.

```python
stream = graph.stream_events({"foo": "foo"}, version="v3")  # 

for subgraph in stream.subgraphs:
    print(subgraph.graph_name, subgraph.path)

    for snapshot in subgraph.values:
        print(subgraph.path, snapshot)
```

If you need the raw protocol events, iterate the stream directly and filter on `event["method"]` and `event["params"]["namespace"]`:

```python
stream = graph.stream_events({"foo": "foo"}, version="v3")
for event in stream:
    if event["method"] == "updates":
        print(event["params"]["namespace"], event["params"]["data"])
```

  
  ```python
  from typing_extensions import TypedDict
  from langgraph.graph.state import StateGraph, START

  # Define subgraph
  class SubgraphState(TypedDict):
      foo: str
      bar: str

  def subgraph_node_1(state: SubgraphState):
      return {"bar": "bar"}

  def subgraph_node_2(state: SubgraphState):
      # note that this node is using a state key ('bar') that is only available in the subgraph
      # and is sending update on the shared state key ('foo')
      return {"foo": state["foo"] + state["bar"]}

  subgraph_builder = StateGraph(SubgraphState)
  subgraph_builder.add_node(subgraph_node_1)
  subgraph_builder.add_node(subgraph_node_2)
  subgraph_builder.add_edge(START, "subgraph_node_1")
  subgraph_builder.add_edge("subgraph_node_1", "subgraph_node_2")
  subgraph = subgraph_builder.compile()

  # Define parent graph
  class ParentState(TypedDict):
      foo: str

  def node_1(state: ParentState):
      return {"foo": "hi! " + state["foo"]}

  builder = StateGraph(ParentState)
  builder.add_node("node_1", node_1)
  builder.add_node("node_2", subgraph)
  builder.add_edge(START, "node_1")
  builder.add_edge("node_1", "node_2")
  graph = builder.compile()

  stream = graph.stream_events({"foo": "foo"}, version="v3")  # 
  for event in stream:
      if event["method"] == "updates":
          print(event["params"]["namespace"], event["params"]["data"])
  ```

  ```
  [] {'node_1': {'foo': 'hi! foo'}}
  ['node_2:e58e5673-a661-ebb0-70d4-e298a7fc28b7'] {'subgraph_node_1': {'bar': 'bar'}}
  ['node_2:e58e5673-a661-ebb0-70d4-e298a7fc28b7'] {'subgraph_node_2': {'foo': 'hi! foobar'}}
  [] {'node_2': {'foo': 'hi! foobar'}}
  ```
  :::

  :::js
  

  1. Set `subgraphs: true` to stream outputs from subgraphs.

  ```
  [[], { node1: { foo: 'hi! foo' } }]
  [['node2:e58e5673-a661-ebb0-70d4-e298a7fc28b7'], { subgraphNode1: { bar: 'bar' } }]
  [['node2:e58e5673-a661-ebb0-70d4-e298a7fc28b7'], { subgraphNode2: { foo: 'hi! foobar' } }]
  [[], { node2: { foo: 'hi! foobar' } }]
  ```
  :::
