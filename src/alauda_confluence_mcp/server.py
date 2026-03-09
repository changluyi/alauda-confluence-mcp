#!/usr/bin/env python3
"""
Alauda Confluence MCP Server - Model Context Protocol server for Confluence integration.

This MCP server provides tools to interact with Confluence:
- Search content using CQL
- Get page details
- List spaces
- Create pages
- Update pages
- Delete pages
- Add comments to pages
"""

import os
import sys
import json
from typing import Any

# Clear proxy settings at startup to avoid connection issues
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

from fastmcp import FastMCP
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

__version__ = "0.1.0"

# Confluence configuration from environment
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "")
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME", "")
CONFLUENCE_PASSWORD = os.environ.get("CONFLUENCE_PASSWORD", "")

# Create MCP server
mcp = FastMCP("alauda-confluence-mcp")


def get_session() -> requests.Session:
    """Create a requests session with proxy disabled."""
    session = requests.Session()
    session.trust_env = False  # Don't read environment proxy settings
    session.proxies = {}  # Clear any proxies
    session.auth = (CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD)
    session.headers.update({"Content-Type": "application/json"})

    # Configure retry strategy
    retry = Retry(total=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def format_content(item: dict) -> dict:
    """Format a Confluence content item for display."""
    return {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "type": item.get("type", ""),
        "status": item.get("status", ""),
        "space": item.get("space", {}).get("key", "") if item.get("space") else "",
        "url": f"{CONFLUENCE_URL}{item.get('_links', {}).get('tinyui', '')}" if item.get("_links") else "",
    }


@mcp.tool()
def search_content(query: str, limit: int = 10, space_key: str = None) -> str:
    """Search Confluence content using text query.

    Args:
        query: Search query string
        limit: Maximum number of results to return (default: 10)
        space_key: Optional space key to limit search scope

    Returns:
        JSON string containing list of matching content
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/content/search"

    # Build CQL query
    cql = f'text ~ "{query}"'
    if space_key:
        cql += f' AND space.key = "{space_key}"'

    params = {
        "cql": cql,
        "limit": limit,
        "expand": "space",
    }

    try:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = [format_content(item) for item in data.get("results", [])]
        return json.dumps(results, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to search content: {str(e)}"})


@mcp.tool()
def get_page(page_id: str) -> str:
    """Get detailed information about a specific Confluence page.

    Args:
        page_id: Page ID or page title (if unique)

    Returns:
        JSON string containing page details including body content
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}"
    params = {"expand": "body.view,space,version"}

    try:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        result = format_content(data)
        result["body"] = data.get("body", {}).get("view", {}).get("value", "")
        result["version"] = data.get("version", {}).get("number", 1)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to get page: {str(e)}"})


@mcp.tool()
def list_spaces(limit: int = 50) -> str:
    """List all available Confluence spaces.

    Args:
        limit: Maximum number of spaces to return (default: 50)

    Returns:
        JSON string containing list of spaces
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/space"
    params = {"limit": limit}

    try:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        spaces = [
            {
                "key": space.get("key", ""),
                "name": space.get("name", ""),
                "type": space.get("type", ""),
                "url": f"{CONFLUENCE_URL}{space.get('_links', {}).get('tinyui', '')}" if space.get("_links") else "",
            }
            for space in data.get("results", [])
        ]
        return json.dumps(spaces, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to list spaces: {str(e)}"})


@mcp.tool()
def get_page_by_title(space_key: str, title: str) -> str:
    """Get a page by its title in a specific space.

    Args:
        space_key: Space key (e.g., 'DEV', 'DOC')
        title: Page title

    Returns:
        JSON string containing page details
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "title": title,
        "expand": "body.view,space,version",
    }

    try:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            return json.dumps({"error": f"Page '{title}' not found in space '{space_key}'"})

        page = results[0]
        result = format_content(page)
        result["body"] = page.get("body", {}).get("view", {}).get("value", "")
        result["version"] = page.get("version", {}).get("number", 1)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to get page: {str(e)}"})


@mcp.tool()
def create_page(space_key: str, title: str, content: str, parent_id: str = None) -> str:
    """Create a new page in Confluence.

    Args:
        space_key: Space key where the page will be created
        title: Page title
        content: Page content in Confluence storage format (HTML-like)
        parent_id: Optional parent page ID to create as child page

    Returns:
        JSON string containing the created page details
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/content"

    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": content, "representation": "storage"}},
    }

    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]

    try:
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        result = format_content(data)
        result["version"] = data.get("version", {}).get("number", 1)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to create page: {str(e)}"})


@mcp.tool()
def update_page(page_id: str, title: str = None, content: str = None, version: int = None, version_message: str = None) -> str:
    """Update an existing Confluence page.

    Args:
        page_id: Page ID to update
        title: New page title (optional, keeps existing if not provided)
        content: New page content in Confluence storage format (optional, keeps existing if not provided)
        version: Current version number (optional, will auto-fetch if not provided)
        version_message: Optional message describing the change

    Returns:
        JSON string containing the updated page details
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()

    # First, get the current page to fetch version and existing content if needed
    try:
        get_url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}"
        get_params = {"expand": "body.storage,version,space"}
        get_response = session.get(get_url, params=get_params, timeout=30)
        get_response.raise_for_status()
        current_page = get_response.json()
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to get current page: {str(e)}"})

    # Determine version number (increment from current)
    current_version = current_page.get("version", {}).get("number", 1)
    new_version = version + 1 if version is not None else current_version + 1

    # Use existing values if not provided
    new_title = title if title is not None else current_page.get("title", "")
    new_content = content if content is not None else current_page.get("body", {}).get("storage", {}).get("value", "")
    space_key = current_page.get("space", {}).get("key", "")

    # Build update payload
    payload = {
        "id": page_id,
        "type": "page",
        "title": new_title,
        "space": {"key": space_key},
        "body": {"storage": {"value": new_content, "representation": "storage"}},
        "version": {"number": new_version},
    }

    if version_message:
        payload["version"]["message"] = version_message

    # Send update request
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}"

    try:
        response = session.put(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        result = format_content(data)
        result["version"] = data.get("version", {}).get("number", new_version)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to update page: {str(e)}"})


@mcp.tool()
def delete_page(page_id: str) -> str:
    """Delete a Confluence page.

    Args:
        page_id: Page ID to delete

    Returns:
        JSON string containing the result of the operation
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/content/{page_id}"

    try:
        response = session.delete(url, timeout=30)
        response.raise_for_status()
        return json.dumps(
            {"success": True, "message": f"Page {page_id} deleted successfully"},
            ensure_ascii=False,
        )
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to delete page: {str(e)}"})


@mcp.tool()
def add_comment(page_id: str, comment: str) -> str:
    """Add a comment to a Confluence page.

    Args:
        page_id: Page ID
        comment: Comment text to add

    Returns:
        JSON string containing the result of the operation
    """
    if not CONFLUENCE_URL:
        return json.dumps({"error": "CONFLUENCE_URL environment variable is not set"})

    session = get_session()
    url = f"{CONFLUENCE_URL}/rest/api/content"

    payload = {
        "type": "comment",
        "container": {"id": page_id, "type": "page"},
        "body": {"storage": {"value": comment, "representation": "storage"}},
    }

    try:
        response = session.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return json.dumps(
            {"success": True, "message": f"Comment added to page {page_id}"},
            ensure_ascii=False,
        )
    except requests.exceptions.RequestException as e:
        return json.dumps({"error": f"Failed to add comment: {str(e)}"})


def main():
    """Entry point for the MCP server."""
    # Validate configuration
    if not all([CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD]):
        print(
            "Warning: CONFLUENCE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_PASSWORD should be set",
            file=sys.stderr,
        )

    # Test connection
    try:
        session = get_session()
        response = session.get(f"{CONFLUENCE_URL}/rest/api/user/current", timeout=10)
        response.raise_for_status()
        user = response.json()
        print(
            f"Connected to Confluence as: {user.get('displayName', user.get('username', 'Unknown'))}",
            file=sys.stderr,
        )
    except Exception as e:
        print(f"Warning: Could not verify Confluence connection: {e}", file=sys.stderr)

    mcp.run()


if __name__ == "__main__":
    main()
