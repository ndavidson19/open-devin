import getpass
import os

# Set environment variables
def set_environment_variables():
    _set_if_undefined("OPENAI_API_KEY")
    _set_if_undefined("GITHUB_TOKEN")
    _set_if_undefined("SQLALCHEMY_DATABASE_URI")



def _set_if_undefined(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Please provide your {var}: ")
