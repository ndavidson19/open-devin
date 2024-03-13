from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation
from langchain_core.messages import (
    FunctionMessage,
)
from .agents import AgentState, agent_node
from .tools import (
    search_and_filter_urls,
    python_repl,
    run_sql_query,
    shell_tool,
    get_issues,
    get_issue,
    comment_on_issue,
)
import functools
import json

# Define Tool Node
tools = [search_and_filter_urls, python_repl, run_sql_query, shell_tool, get_issues, get_issue, comment_on_issue]
tool_executor = ToolExecutor(tools)

def tool_node(state):
    messages = state["messages"]
    last_message = messages[-1]
    tool_input = json.loads(last_message.additional_kwargs["function_call"]["arguments"])
    if len(tool_input) == 1 and "__arg1" in tool_input:
        tool_input = next(iter(tool_input.values()))
    tool_name = last_message.additional_kwargs["function_call"]["name"]
    action = ToolInvocation(tool=tool_name, tool_input=tool_input)
    response = tool_executor.invoke(action)
    function_message = FunctionMessage(content=f"{tool_name} response: {str(response)}", name=action.tool)
    return {"messages": [function_message]}

# Define Edge Logic
def router(state):
    messages = state["messages"]
    last_message = messages[-1]
    if "function_call" in last_message.additional_kwargs:
        return "call_tool"
    if "FINAL ANSWER" in last_message.content:
        return "end"
    return "continue"

# Define the Graph
def setup_graph(research_agent, chart_agent):
    workflow = StateGraph(AgentState)

    research_node = functools.partial(agent_node, agent=research_agent, name="Researcher")
    chart_node = functools.partial(agent_node, agent=chart_agent, name="Chart Generator")

    workflow.add_node("Researcher", research_node)
    workflow.add_node("Chart Generator", chart_node)
    workflow.add_node("call_tool", tool_node)

    workflow.add_conditional_edges(
        "Researcher",
        router,
        {"continue": "Chart Generator", "call_tool": "call_tool", "end": END},
    )
    workflow.add_conditional_edges(
        "Chart Generator",
        router,
        {"continue": "Researcher", "call_tool": "call_tool", "end": END},
    )

    workflow.add_conditional_edges(
        "call_tool",
        lambda x: x["sender"],
        {
            "Researcher": "Researcher",
            "Chart Generator": "Chart Generator",
        },
    )
    workflow.set_entry_point("Researcher")
    return workflow.compile()
