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

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def tool_node(state):
    try:
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
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return {"messages": [FunctionMessage(content=f"Error: {e}", name='Error')]}

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
def setup_graph(cot_planner_agent, code_gen_agent, web_search_agent):
    workflow = StateGraph(AgentState)

    # Create nodes for each agent
    cot_planner_node = functools.partial(agent_node, agent=cot_planner_agent, name="CoT Planner")
    code_gen_node = functools.partial(agent_node, agent=code_gen_agent, name="Code Generator")
    web_search_node = functools.partial(agent_node, agent=web_search_agent, name="Web Searcher")

    # Add nodes to the workflow
    workflow.add_node("CoT Planner", cot_planner_node)
    workflow.add_node("Code Generator", code_gen_node)
    workflow.add_node("Web Searcher", web_search_node)
    workflow.add_node("call_tool", tool_node)

    # Define edges and conditions for transitioning between nodes
    workflow.add_conditional_edges(
        "CoT Planner",
        router,
        {
            "continue": "Code Generator",  # Pass the plan to code generator to execute
            "call_tool": "call_tool",  # Call a specific tool if needed
            "end": END,  # End if the final answer is reached
        },
    )

    workflow.add_conditional_edges(
        "Code Generator",
        router,
        {
            "continue": "Web Searcher",  # If code gen needs more info, go to web search
            "call_tool": "call_tool",  # Or call a specific tool
            "end": END,  # Or end if the task is completed
        },
    )

    workflow.add_conditional_edges(
        "Web Searcher",
        router,
        {
            "continue": "CoT Planner",  # If web search finds info, go back to planning
            "call_tool": "call_tool",  # Or call a tool for direct action
            "end": END,  # Or end if web search provides a final solution
        },
    )

    workflow.add_conditional_edges(
        "call_tool",
        lambda x: x["sender"],  # Each agent node updates the 'sender' field
        {
            "CoT Planner": "CoT Planner",
            "Code Generator": "Code Generator",
            "Web Searcher": "Web Searcher",  # Return control to the agent that called the tool
        },
    )

    # Set the entry point for the graph
    workflow.set_entry_point("CoT Planner")
    return workflow.compile()
