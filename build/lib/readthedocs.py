from typing import Any, List, Optional
import httpx
import asyncio
import sys
import os
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
import traceback

# Initialize FastMCP server
mcp = FastMCP("readthedocs")

# Constants
READTHEDOCS_API_BASE = "https://readthedocs.org/api/v3"
USER_AGENT = "readthedocs-mcp/1.0"
CACHE_TTL = 3600  # Cache time to live in seconds

# Get API token from environment or set directly
# Either:
# 1. Set API_TOKEN directly here:
# API_TOKEN = "your_token_here"  
# 
# 2. Or use environment variable (recommended):
API_TOKEN = os.environ.get("985ba346357e55d9b96eb6fd7148acc8eddbd735")

# Simple in-memory cache
cache = {}

# For debugging
print(f"Python version: {sys.version}", file=sys.stderr)
print(f"Using API token: {'Yes' if API_TOKEN else 'No'}", file=sys.stderr)

async def make_readthedocs_request(url: str, token: Optional[str] = None) -> dict[str, Any] | None:
    """Make a request to the Read the Docs API with proper error handling."""
    # Check cache first
    if url in cache and cache[url]["expires"] > asyncio.get_event_loop().time():
        return cache[url]["data"]
    
    # Use the provided token, or fall back to the global token
    token_to_use = token or API_TOKEN
    
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    # Add authentication if token provided
    if token_to_use:
        headers["Authorization"] = f"Token {token_to_use}"
        print(f"Using token for request to: {url}", file=sys.stderr)
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            # Cache the result
            cache[url] = {
                "data": data,
                "expires": asyncio.get_event_loop().time() + CACHE_TTL
            }
            
            return data
        except Exception as e:
            print(f"Error requesting {url}: {str(e)}", file=sys.stderr)
            return None

async def fetch_page_content(url: str) -> Optional[str]:
    """Fetch the content of a documentation page."""
    # Check cache first
    if url in cache and cache[url]["expires"] > asyncio.get_event_loop().time():
        return cache[url]["data"]
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            print(f"Fetching content from: {url}", file=sys.stderr)
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
            print(f"Successfully fetched content. Status: {response.status_code}", file=sys.stderr)
            
            # Parse the HTML to extract the main content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try multiple selectors for different themes and page structures
            content = None
            
            # Common content selectors in different themes
            content_selectors = [
                ('div', {'role': 'main'}),
                ('div', {'class': 'document'}),
                ('div', {'class': 'rst-content'}),
                ('article', {'role': 'main'}),
                ('main', {}),
                ('div', {'class': 'section'}),
                ('div', {'id': 'content'}),
                ('div', {'class': 'content'}),
            ]
            
            # Try each selector until we find content
            for tag, attrs in content_selectors:
                content = soup.find(tag, attrs)
                if content and len(content.get_text(strip=True)) > 100:  # Ensure there's substantial content
                    print(f"Found content using selector: {tag}, {attrs}", file=sys.stderr)
                    break
            
            # If we still didn't find content, try the document body with title
            if not content or len(content.get_text(strip=True)) < 100:
                print("Standard content selectors failed. Trying body content...", file=sys.stderr)
                title = soup.find('title')
                title_text = title.get_text(strip=True) if title else "Documentation"
                
                # Get the body content
                body = soup.find('body')
                if body:
                    # Strip navigation, header, footer elements
                    for nav in body.find_all(['nav', 'header', 'footer']):
                        nav.decompose()
                    
                    content = body
            
            if content:
                # Extract and clean up the text
                extracted_text = content.get_text(separator='\n')
                
                # Remove excessive whitespace
                extracted_text = '\n'.join(line.strip() for line in extracted_text.split('\n') if line.strip())
                
                # Cache the result
                cache[url] = {
                    "data": extracted_text,
                    "expires": asyncio.get_event_loop().time() + CACHE_TTL
                }
                
                return extracted_text
            
            print(f"Could not find suitable content in the page", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error fetching page: {e}", file=sys.stderr)
            return None

@mcp.tool()
async def search_docs(query: str, project: str, max_results: int = 10, token: Optional[str] = None) -> str:
    """Search for content in a Read the Docs project documentation.
    
    Args:
        query: The search query
        project: The project slug (e.g., 'python', 'django')
        max_results: Maximum number of results to return
        token: Optional API token for authentication
    """
    # Use the official Read the Docs search API with proper endpoint
    search_url = f"{READTHEDOCS_API_BASE}/search/"
    
    # Format the query parameters according to Read the Docs API documentation
    formatted_query = f"project:{project} {query}"
    
    params = {
        "q": formatted_query,
        "page_size": max_results
    }
    
    print(f"Using Read the Docs search API: {search_url} with query: {formatted_query}", file=sys.stderr)
    
    # Prepare headers with authentication if token is provided
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    
    token_to_use = token or API_TOKEN
    if token_to_use:
        headers["Authorization"] = f"Token {token_to_use}"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(search_url, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            search_data = response.json()
            
            print(f"Search API response received, status: {response.status_code}", file=sys.stderr)
            
            if not search_data.get("results") or len(search_data["results"]) == 0:
                return f"No search results found for '{query}' in {project} documentation."
            
            # Format the results
            formatted_results = f"Search results for '{query}' in {project} documentation:\n\n"
            
            for i, result in enumerate(search_data["results"][:max_results], 1):
                # Get basic information
                title = result.get("title", "Untitled")
                
                # Build the full URL from domain and path
                domain = result.get("domain", "")
                path = result.get("path", "")
                full_url = f"{domain}{path}" if domain and path else ""
                
                # Get project and version info
                project_info = result.get("project", {})
                project_slug = project_info.get("slug", project) if isinstance(project_info, dict) else project
                
                version_info = result.get("version", {})
                version_slug = version_info.get("slug", "latest") if isinstance(version_info, dict) else "latest"
                
                # Extract content from blocks
                blocks = result.get("blocks", [])
                excerpt = ""
                
                for block in blocks:
                    if block.get("type") == "section" and block.get("content"):
                        excerpt = block.get("content")
                        break
                
                # Ensure we have an URL
                if not full_url and project_slug and version_slug:
                    # If we have a section ID in the first block, use it
                    section_id = ""
                    if blocks and blocks[0].get("id"):
                        section_id = f"#{blocks[0].get('id')}"
                    
                    # Get title as path component if available
                    if blocks and blocks[0].get("name"):
                        path_component = blocks[0].get("name")
                    else:
                        path_component = title.lower().replace(' ', '-').replace('(', '').replace(')', '')
                    
                    # Construct URL with proper language code (/en/)
                    full_url = f"https://{project_slug}.readthedocs.io/en/{version_slug}/{path_component}.html{section_id}"
                
                # Format the result entry
                formatted_results += f"{i}. {title}\n"
                formatted_results += f"   Link: {full_url}\n"
                if excerpt:
                    formatted_results += f"   {excerpt}\n"
                formatted_results += "\n"
            
            # Add pagination info if available
            if "next" in search_data and search_data.get("count", 0) > max_results:
                formatted_results += f"\nShowing {min(max_results, len(search_data['results']))} of {search_data.get('count', 0)} results. Use a more specific query to narrow down the results."
            
            # Add instruction for viewing content
            formatted_results += "\nTo view the full content of a result, use the get_page tool with the appropriate project, version, and path parameters."
            
            return formatted_results
            
        except Exception as e:
            print(f"Error using search API: {str(e)}", file=sys.stderr)
            traceback_str = traceback.format_exc()
            print(f"Traceback: {traceback_str}", file=sys.stderr)
            
            return f"Error searching for '{query}' in {project} documentation: {str(e)}"

@mcp.tool()
async def get_page(project: str, version: str, path: str, token: Optional[str] = None) -> str:
    """Get a specific documentation page.
    
    Args:
        project: The project slug (e.g., 'python', 'django')
        version: The documentation version (e.g., 'latest', 'stable', '3.0')
        path: The page path (e.g., 'tutorial/index.html')
        token: Optional API token for authentication
    """
    # Try to validate the project exists
    project_details = await make_readthedocs_request(f"{READTHEDOCS_API_BASE}/projects/{project}/", token)
    if not project_details:
        print(f"Project '{project}' not found via API. Will try to access directly.", file=sys.stderr)
    
    # Ensure path doesn't start with a slash
    if path.startswith('/'):
        path = path[1:]
    
    # Build the URL for the documentation page with language code
    url = f"https://{project}.readthedocs.io/en/{version}/{path}"
    print(f"Attempting to fetch documentation at: {url}", file=sys.stderr)
    
    content = await fetch_page_content(url)
    if not content:
        # Try without the path or with index.html appended
        if not path.endswith('/') and not path.endswith('index.html'):
            # Try with trailing slash
            print(f"First attempt failed. Trying with trailing slash...", file=sys.stderr)
            alternate_url = f"https://{project}.readthedocs.io/en/{version}/{path}/"
            content = await fetch_page_content(alternate_url)
            
            if not content:
                # Try with index.html
                print(f"Second attempt failed. Trying with index.html...", file=sys.stderr)
                alternate_url = f"https://{project}.readthedocs.io/en/{version}/{path}/index.html"
                content = await fetch_page_content(alternate_url)
        
        if not content:
            return f"Unable to fetch the page at {url} or its variations. Please check if the project, version, and path are correct."
    
    # Format the content to be more readable
    # Truncate if too long
    if len(content) > 8000:
        content = content[:8000] + "...\n\n[Content truncated due to length. Use search_docs to find specific information.]"
    
    return f"Documentation for {project} ({version}) - {path}:\n\n{content}"

@mcp.tool()
async def list_projects(query: Optional[str] = None, limit: int = 10, token: Optional[str] = None) -> str:
    """List available documentation projects.
    
    Args:
        query: Optional search term to filter projects
        limit: Maximum number of projects to return
        token: Optional API token for authentication
    """
    url = f"{READTHEDOCS_API_BASE}/projects/"
    params = []
    
    if query:
        params.append(f"q={query}")
    if limit:
        params.append(f"limit={limit}")
    
    if params:
        url += "?" + "&".join(params)
    
    print(f"Requesting projects from URL: {url}", file=sys.stderr)
    
    try:
        # First, try direct API request
        response = await make_readthedocs_request(url, token)
        
        if not response:
            print(f"API request failed. Trying alternative approach...", file=sys.stderr)
            # If direct API fails, try alternative approach - search the project directly
            project_url = f"{READTHEDOCS_API_BASE}/projects/{query}/"
            project_response = await make_readthedocs_request(project_url, token)
            
            if project_response:
                # If project exists directly, create a fake "results" list with just this project
                print(f"Found project directly: {query}", file=sys.stderr)
                return format_project_list([project_response])
            else:
                # Try searching on the site directly
                print(f"Trying to search readthedocs.org website for: {query}", file=sys.stderr)
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    try:
                        headers = {}
                        if token or API_TOKEN:
                            token_to_use = token or API_TOKEN
                            headers["Authorization"] = f"Token {token_to_use}"
                            
                        search_url = f"https://readthedocs.org/search/?q={query}"
                        search_response = await client.get(search_url, headers=headers, timeout=10.0)
                        search_response.raise_for_status()
                        
                        soup = BeautifulSoup(search_response.text, 'html.parser')
                        project_items = soup.select('.module-item')
                        
                        if project_items:
                            print(f"Found {len(project_items)} projects on website search", file=sys.stderr)
                            projects = []
                            for item in project_items[:limit]:
                                name_elem = item.select_one('h3 a')
                                if name_elem:
                                    name = name_elem.get_text(strip=True)
                                    slug = name.lower().replace(' ', '-')
                                    desc_elem = item.select_one('.module-item-desc')
                                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                                    projects.append({
                                        'name': name,
                                        'slug': slug,
                                        'description': description
                                    })
                            return format_project_list(projects)
                    except Exception as e:
                        print(f"Error in website search: {str(e)}", file=sys.stderr)
        
        # Handle normal API response
        if response and "results" in response:
            return format_project_list(response["results"])
        else:
            print(f"API response doesn't contain results. Response: {response}", file=sys.stderr)
            return f"No projects found{' matching the query' if query else ''}."
    
    except Exception as e:
        print(f"Error in list_projects: {str(e)}", file=sys.stderr)
        return f"Error fetching projects: {str(e)}"

def format_project_list(projects: List[dict]) -> str:
    """Format a list of projects into a readable string."""
    if not projects:
        return "No projects found."
    
    formatted_list = "Read the Docs projects:\n\n"
    
    for i, project in enumerate(projects, 1):
        formatted_list += f"{i}. {project['name']}\n"
        formatted_list += f"   Slug: {project['slug']}\n"
        if 'description' in project and project['description']:
            formatted_list += f"   Description: {project['description']}\n"
        formatted_list += f"   URL: https://{project['slug']}.readthedocs.io\n\n"
    
    return formatted_list

@mcp.tool()
async def get_project_versions(project: str, active: bool = True, token: Optional[str] = None) -> str:
    """Get available versions for a project.
    
    Args:
        project: The project slug
        active: Whether to show only active versions (default: True)
        token: Optional API token for authentication
    """
    url = f"{READTHEDOCS_API_BASE}/projects/{project}/versions/"
    if active:
        url += "?active=true"
    
    response = await make_readthedocs_request(url, token)
    if not response or "results" not in response:
        return f"Unable to fetch versions for project '{project}'."
    
    versions = response["results"]
    if not versions:
        return f"No versions found for project '{project}'."
    
    formatted_versions = f"Available versions for {project}:\n\n"
    
    for i, version in enumerate(versions, 1):
        formatted_versions += f"{i}. {version['slug']}"
        if version.get('active', False):
            formatted_versions += " (active)"
        formatted_versions += "\n"
        if 'identifier' in version:
            formatted_versions += f"   Identifier: {version['identifier']}\n"
        formatted_versions += f"   URL: https://{project}.readthedocs.io/en/{version['slug']}/\n\n"
    
    return formatted_versions

@mcp.tool()
async def get_toc(project: str, version: str = "latest", token: Optional[str] = None) -> str:
    """Get the table of contents for a project.
    
    Args:
        project: The project slug
        version: The documentation version
        token: Optional API token for authentication
    """
    # Try to validate project exists
    project_details = await make_readthedocs_request(f"{READTHEDOCS_API_BASE}/projects/{project}/", token)
    if not project_details:
        print(f"Project '{project}' not found via API. Will try to access directly.", file=sys.stderr)
        # Even if the API doesn't find it, the project might still exist on the site
    
    # Get the homepage which usually contains the TOC
    url = f"https://{project}.readthedocs.io/{version}/"
    print(f"Attempting to fetch TOC from: {url}", file=sys.stderr)
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
            print(f"Successfully fetched page. Status: {response.status_code}", file=sys.stderr)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the table of contents - try different selectors for different themes
            toc = (soup.find('div', {'class': 'toctree-wrapper'}) or 
                   soup.find('nav', {'class': 'toc'}) or
                   soup.find('div', {'class': 'sphinxsidebarwrapper'}) or
                   soup.find('div', {'class': 'sidebar-tree'}))
            
            if not toc:
                # If we can't find a dedicated TOC section, look for any list of links
                print(f"No standard TOC found. Looking for alternative link collections.", file=sys.stderr)
                toc = soup.find('ul')
            
            if not toc:
                return f"Unable to find table of contents for {project} ({version}). The documentation may have a non-standard structure."
            
            # Format the TOC
            formatted_toc = f"Table of Contents for {project} ({version}):\n\n"
            
            links = toc.find_all('a')
            print(f"Found {len(links)} links in TOC", file=sys.stderr)
            
            for link in links:
                # Get the text and link
                text = link.get_text(strip=True)
                href = link.get('href')
                
                if text and href:
                    # Calculate indentation based on CSS classes or parent elements
                    indent_level = 0
                    parent_li = link.find_parent('li')
                    if parent_li:
                        # Check if there are parent lists
                        indent_level = len(parent_li.find_parents('li'))
                    
                    # Add to formatted TOC
                    formatted_toc += f"{'  ' * indent_level}- {text}: {href}\n"
            
            return formatted_toc
        except Exception as e:
            print(f"Error fetching table of contents: {str(e)}", file=sys.stderr)
            return f"Error fetching table of contents: {str(e)}"

@mcp.tool()
async def get_project_details(project: str, token: Optional[str] = None) -> str:
    """Get detailed information about a project.
    
    Args:
        project: The project slug
        token: Optional API token for authentication
    """
    url = f"{READTHEDOCS_API_BASE}/projects/{project}/"
    
    response = await make_readthedocs_request(url, token)
    if not response:
        return f"Project '{project}' not found or is not accessible."
    
    # Format project details
    formatted_details = f"Project Details for {response.get('name', project)}:\n\n"
    
    # Basic information
    formatted_details += f"Slug: {response.get('slug', 'N/A')}\n"
    formatted_details += f"Description: {response.get('description', 'No description available')}\n"
    formatted_details += f"Homepage: {response.get('homepage', 'N/A')}\n"
    formatted_details += f"Language: {response.get('language', {}).get('name', 'N/A')}\n"
    formatted_details += f"Programming Language: {response.get('programming_language', {}).get('name', 'N/A')}\n"
    
    # Repository information
    if 'repository' in response:
        formatted_details += f"\nRepository:\n"
        formatted_details += f"  URL: {response['repository'].get('url', 'N/A')}\n"
        formatted_details += f"  Type: {response['repository'].get('type', 'N/A')}\n"
    
    # Documentation links
    formatted_details += f"\nDocumentation:\n"
    formatted_details += f"  URL: https://{project}.readthedocs.io/\n"
    
    return formatted_details

if __name__ == "__main__":
    # Initialize and run the server
    print("Starting ReadTheDocs MCP server...", file=sys.stderr)
    mcp.run(transport='stdio') 