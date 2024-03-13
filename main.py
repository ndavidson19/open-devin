from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_community.utilities import SQLDatabase
from devin.config import set_environment_variables
from devin.agents import create_agent
from devin.graph import setup_graph
from devin.tools import (
    python_repl,
    search_and_filter_urls,
    get_issues,
    get_issue,
    comment_on_issue,
    run_sql_query,
    shell_tool,
)
from github import Github
import os
import random

def main():
    set_environment_variables()

    # Initialize ChatOpenAI with OpenAI API Key
    llm = ChatOpenAI(model="gpt-4-1106-preview")

    # Create CoT Planner/Routing Agent
    cot_planner_agent = create_agent(
        llm,
        [get_issues, get_issue, comment_on_issue],
        system_message="Create a detailed plan to address a GitHub issue.",
    )

    # Create Code Generation Agent
    code_gen_agent = create_agent(
        llm,
        [python_repl, shell_tool],  # Assuming shell_tool is well defined to clone repos and manage files
        system_message="Execute code changes based on the plan.",
    )

    # Create Web Search Agent
    web_search_agent = create_agent(
        llm,
        [search_and_filter_urls],
        system_message="Search the web for solutions to coding problems.",
    )

    # Setup the graph to include the agents and define how they interact
    graph = setup_graph(cot_planner_agent, code_gen_agent, web_search_agent)

    # User inputs the GitHub repository as part of the prompt
    user_prompt = input("Please enter the GitHub repository (e.g., 'owner/repo'): ")
    repository = user_prompt.strip()

    # Fetch issues from the repository
    issues = get_issues(repository)
    if not issues:
        print("No open issues found in the repository.")
        return

    # Randomly pick an issue to solve
    selected_issue = random.choice(issues.split('\n'))
    issue_number = int(selected_issue.split(":")[0])
    print(f"Selected issue to solve: {selected_issue}")

    # Stream the process through the graph
    for s in graph.stream(
        {
            "messages": [
                HumanMessage(content=f"Generate a plan to fix issue number {issue_number} in the repository {repository}.")
            ],
        },
        {"recursion_limit": 150},
    ):
        print(s)
        print("----")

if __name__ == "__main__":
    main()
