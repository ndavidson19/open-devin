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
)
from github import Github
import os

def main():

    set_environment_variables()
    #db = SQLDatabase.from_uri(os.environ["SQLALCHEMY_DATABASE_URI"])

    llm = ChatOpenAI(model="gpt-4-1106-preview")

    # Assume these agents have been defined with the appropriate system messages
    cot_planner_agent = create_agent(
        llm,
        [search_and_filter_urls, get_issues, get_issue, comment_on_issue],
        system_message="You will plan and route tasks for software engineering.",
    )

    code_gen_agent = create_agent(
        llm,
        [python_repl, run_sql_query],  # You can add ShellTool if needed
        system_message="You will execute and manage code generation.",
    )

    # Setup the graph to include the agents and define how they interact
    graph = setup_graph(cot_planner_agent, code_gen_agent)

    # Example task: Retrieve and store GitHub issues in the database
    for s in graph.stream(
        {
            "messages": [
                HumanMessage(
                    content="Retrieve issues from the llama.cpp GitHub repository https://github.com/ggerganov/llama.cpp and try to fix one of them."
                )
            ],
        },
        {"recursion_limit": 150},
    ):
        print(s)
        print("----")

if __name__ == "__main__":
    main()
