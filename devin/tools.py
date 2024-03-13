from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL
from typing import Annotated
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List
from langchain_community.tools import ShellTool
import sqlalchemy as sa
import os

shell_tool = ShellTool()
# Define tools
repl = PythonREPL()

@tool
def run_sql_query(query: str, parameters: dict = None, fetch_mode: str = "cursor") -> str:
    """Run an SQL query on the SQLite database and return the results."""
    result = db.run(query, parameters=parameters, fetch=fetch_mode)
    return result
'''
# Store scraped data in the database
insert_query = "INSERT INTO scraped_data (url, content) VALUES (:url, :content)"
for url, content in scraped_data.items():
    run_sql_query(insert_query, parameters={"url": url, "content": content})

# Retrieve stored data from the database
select_query = "SELECT * FROM scraped_data WHERE url LIKE :search_term"
search_term = "%stackoverflow%"
stored_data = run_sql_query(select_query, parameters={"search_term": search_term}, fetch_mode="all")


'''

@tool
def python_repl(code: Annotated[str, "The python code to execute to generate your chart."]):
    """Execute Python code in a REPL."""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    return f"Succesfully executed:\n```python\n{code}\n```\nStdout: {result}"


@tool
def search_and_filter_urls(search_terms: List[str], trusted_domains: List[str]) -> List[str]:
    """Search the web for the given terms and filter results by trusted domains."""
    search_results = []
    for term in search_terms:
        # Replace spaces with '+' for the search query
        query = term.replace(' ', '+')
        # Perform a Google search (note: scraping Google may violate their TOS)
        response = requests.get(f'https://www.google.com/search?q={query}')
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find all search result links
        for link in soup.find_all('a', href=True):
            url = link['href']
            # Filter out URLs that don't start with 'http'
            if url.startswith('http'):
                # Parse the URL to get the domain
                domain = urlparse(url).netloc
                # Check if the domain is in the list of trusted domains
                if any(trusted_domain in domain for trusted_domain in trusted_domains):
                    search_results.append(url)
    return search_results
from github import Github

@tool
def get_issues(repository_name: str) -> str:
    """Fetches issues from the repository."""
    github_client = Github(login_or_token=os.environ["GITHUB_TOKEN"])

    repo = github_client.get_repo(repository_name)
    issues = repo.get_issues(state="open")
    return "\n".join([f"{issue.number}: {issue.title}" for issue in issues])

@tool
def get_issue(repository_name: str, issue_number: int) -> str:
    """Fetches details about a specific issue."""
    github_client = Github(login_or_token=os.environ["GITHUB_TOKEN"])

    repo = github_client.get_repo(repository_name)
    issue = repo.get_issue(number=issue_number)
    return f"Title: {issue.title}\nBody: {issue.body}"

@tool
def comment_on_issue(repository_name: str, issue_number: int, comment: str) -> str:
    """Posts a comment on a specific issue."""
    github_client = Github(login_or_token=os.environ["GITHUB_TOKEN"])

    repo = github_client.get_repo(repository_name)
    issue = repo.get_issue(number=issue_number)
    issue.create_comment(body=comment)
    return f"Commented on issue #{issue_number}"
