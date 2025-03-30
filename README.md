# ReadTheDocs MCP Server

This is a Multi-Context Protocol (MCP) server that enables LLMs to interact with documentation hosted on Read the Docs.

## Features

- Search for content in Read the Docs documentation
- Get specific documentation pages
- List available documentation projects
- Get table of contents for a project
- Get project versions
- Get detailed project information
- Support for ReadTheDocs API token authentication

## Installation

### Using pip

```bash
# Install the package
pip install .

# For development dependencies
pip install -e .[dev]
```

### Using uv (recommended)

```bash
# Create and activate a virtual environment
python -m uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install .

# For development dependencies
uv pip install -e .[dev]

# Run the server
python readthedocs.py
```

## Available MCP Tools

The server provides the following tools:

1. `list_projects`: List available documentation projects
2. `get_project_details`: Get detailed information about a specific project
3. `get_project_versions`: Get available versions for a project
4. `get_page`: Get a specific documentation page
5. `search_docs`: Search for content within a project's documentation
6. `get_toc`: Get the table of contents for a project

## API Token (Important)

For higher rate limits, access to private projects, and better search results, it's **highly recommended** to use an API token:

1. Get a token from Read the Docs:
   - Log in to Read the Docs
   - Go to Account Settings > API v3 > Tokens
   - Create a new token

2. Method 1 - Add the token to your MCP server code:
   ```python
   # In readthedocs.py
   API_TOKEN = "your_token_here"  # Replace with your actual token
   ```

3. Method 2 - Pass the token when calling tools:
   ```python
   # When using the MCP client directly
   result = await server.call_tool(
       "search_docs",
       {
           "query": "tutorial",
           "project": "python",
           "max_results": 3,
           "token": "your_token_here"  # Add your token here
       }
   )
   ```

4. Method 3 - Set the token in your Claude Desktop configuration:
   ```json
   {
     "mcpServers": {
       "readthedocs": {
         "command": "python",
         "args": [
           "/ABSOLUTE/PATH/TO/readthedocs.py"
         ],
         "env": {
           "READTHEDOCS_TOKEN": "your_token_here"
         }
       }
     }
   }
   ```
   Then update the `readthedocs.py` file to use this environment variable:
   ```python
   import os
   API_TOKEN = os.environ.get("READTHEDOCS_TOKEN")
   ```

The token helps with:
- Higher rate limits (60 requests per minute instead of 10)
- Access to private documentation projects
- Better search results from the API
- More reliable project search

## Usage with Claude for Desktop

1. Install Claude for Desktop
2. Configure the `claude_desktop_config.json` file:

```json
{
  "mcpServers": {
    "readthedocs": {
      "command": "python",
      "args": [
        "/ABSOLUTE/PATH/TO/readthedocs.py"
      ],
      "env": {
        "READTHEDOCS_TOKEN": "your_token_here"  // Optional but recommended
      }
    }
  }
}
```

3. Start Claude for Desktop and interact with Read the Docs documentation:
   - "Show me the Django tutorial"
   - "Search the Python docs for 'list comprehension'"
   - "List available documentation projects"
   - "Get the table of contents for Pandas"
   - "What versions of FastAPI are available?"
   - "Show me details about the requests project"
   - "Find the synxflow documentation"

## Usage with Cursor IDE

1. Install Cursor IDE from [cursor.sh](https://cursor.sh/)
2. Open Cursor settings and navigate to the MCP Servers section
3. Add a new MCP server with the following configuration:
   - Name: readthedocs
   - Command: python
   - Args: ["/ABSOLUTE/PATH/TO/readthedocs.py"]
   - Environment Variables: Add READTHEDOCS_TOKEN if using Method 3 for token
   
   Or use the JSON configuration:
   ```json
   {
     "readthedocs": {
       "command": "python",
       "args": ["/ABSOLUTE/PATH/TO/readthedocs.py"],
       "env": {
         "READTHEDOCS_TOKEN": "your_token_here"  // Optional but recommended
       }
     }
   }
   ```

4. Restart Cursor or reload the MCP servers
5. Use the ReadTheDocs functionality through Cursor's AI features:
   - "Show me Python's context managers documentation"
   - "Search Flask docs for routing"
   - "Get the list of top projects on Read the Docs"

## Debugging Tips

If you encounter issues with the MCP server:

1. Make sure you're using Python 3.10 or later (required for MCP)
2. Check that your Python path is correctly specified in the configuration
3. Look for error messages in the logs
4. Try running the readthedocs.py script directly to see any error output
5. For rate limit errors or "project not found" errors, add an API token
6. Check if the project URL works directly in a browser

## Usage with Custom Client

You can use the included `client_test.py` script to test the server:

```bash
python client_test.py
```

## Docker

Build and run the Docker container:

```bash
# Build the image
docker build -t readthedocs-mcp .

# Run the container
docker run -it readthedocs-mcp
```

## Testing

Run the tests:

```bash
pytest test_readthedocs.py
```

## Direct Usage

If you just want to test the server without installing it, you can run it directly:

```bash
# Install dependencies
pip install httpx beautifulsoup4 mcp[cli]
# or with uv
uv pip install httpx beautifulsoup4 mcp[cli]

# Run the server
python readthedocs.py
``` # readthedocsmcp
# readthedocsmcp
