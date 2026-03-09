# This is an implementation of https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""OCI Documentation MCP Server implementation."""

import argparse
import httpx
import os
import re
import sys
import requests

from oci_documentation_mcp_server.models import (
    SearchResult,
)

from oci_documentation_mcp_server.util import (
    extract_content_from_html,
    format_documentation_result,
    is_html_content
)
from fastmcp import FastMCP, Context
from loguru import logger
from pydantic import AnyUrl, Field
from typing import List, Union


logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'WARNING'))

DEFAULT_HEADERS = {
    "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    "sec-ch-ua-mobile": '?0',
    "sec-ch-ua": '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    "accept-language": '*/en-US,en;q=0.9',
    'Content-Type': 'application/json',
}

ORACLE_SEARCH_API_URL = 'https://docs.oracle.com/apps/ohcsearchclient/api/v2/search/pages'
ORACLE_SEARCH_PARAMS = {
    "size": 10,
    "pg": 1,
    "product": "en/cloud/oracle-cloud-infrastructure",
    "showfirstpage": "true",
    "lang": "en",
    "snippet": "true"
}


mcp = FastMCP(
    'oci-documentation-mcp-server',
    instructions="""
    # OCI Documentation MCP Server

    This server provides tools to access public OCI documentation, search for content, and get recommendations.

    ## Best Practices

    - For long documentation pages, make multiple calls to `read_documentation` with different `start_index` values for pagination
    - For very long documents (>30,000 characters), stop reading if you've found the needed information
    - When searching, use specific technical terms rather than general phrases
    - Use `recommend` tool to discover related content that might not appear in search results
    - For recent updates to a service, get an URL for any page in that service, then check the **New** section of the `recommend` tool output on that URL
    - If multiple searches with similar terms yield insufficient results, pivot to using `recommend` to find related pages.
    - Always cite the documentation URL when providing information to users

    ## Tool Selection Guide

    - Use `search_documentation` when: You need to find documentation about a specific OCI service or feature
    - Use `read_documentation` when: You have a specific documentation URL and need its content
    - Use `recommend` when: You want to find related content to a documentation page you're already viewing or need to find newly released information
    - Use `recommend` as a fallback when: Multiple searches have not yielded the specific information needed
    """,
)



@mcp.tool
async def search_documentation(
    ctx: Context,
    search_phrase: str = Field(description='Search phrase to use'),
    limit: int = Field(
        default=3,
        description='Maximum number of results to return',
        ge=1,
        le=10,
        ),
    ) -> List[SearchResult]:
    """Search OCI documentation using the Oracle Documentation Search API.

    ## Usage

    This tool searches across all OCI documentation for pages matching your search phrase.
    Use it to find relevant documentation when you don't have a specific URL.

    ## Search Tips

    - Use specific technical terms rather than general phrases
    - Include service names to narrow results (e.g., "OCI Object Storage bucket versioning" instead of just "versioning")
    - Use quotes for exact phrase matching (e.g., "Using Instance Configurations and Instance Pools")
    - Include abbreviations and alternative terms to improve results

    ## Result Interpretation

    Each result includes:
    - title: The documentation page title
    - url: The documentation page URL
    - description: A brief excerpt or summary

    Args:
        ctx: MCP context for logging and error handling
        search_phrase: Search phrase to use
        limit: Maximum number of results to return

    Returns:
        List of search results with URLs, titles, and context snippets
    """
    logger.info(f'Searching OCI documentation for: {search_phrase}')

    params = ORACLE_SEARCH_PARAMS.copy()
    params['q'] = search_phrase
    params['size'] = limit

    try:
        response = requests.get(
            ORACLE_SEARCH_API_URL,
            params=params,
            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'},
            timeout=30,
        )
    except requests.RequestException as e:
        error_msg = f'Error searching OCI docs: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return [SearchResult(title='', url='', description=error_msg)]

    if response.status_code >= 400:
        error_msg = f'Error searching OCI docs: status code {response.status_code}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return [SearchResult(title='', url='', description=error_msg)]

    try:
        data = response.json()
    except Exception as e:
        error_msg = f'Error parsing search response: {str(e)}'
        logger.error(error_msg)
        await ctx.error(error_msg)
        return [SearchResult(title='', url='', description=error_msg)]

    results = []
    hits = data.get('hits', [])
    
    for hit in hits[:limit]:
        source = hit.get('_source', {})
        title = source.get('title', 'Untitled')
        url = hit.get('_id', '')
        
        highlight = hit.get('highlight', {})
        description = None
        
        if 'description' in highlight and highlight['description']:
            desc_val = highlight['description']
            description = desc_val[0] if isinstance(desc_val, list) else desc_val
        elif 'body' in highlight and highlight['body']:
            body_val = highlight['body']
            description = body_val[0] if isinstance(body_val, list) else body_val
        
        if description:
            description = re.sub(r'<[^>]+>', '', description)
            description = description.replace('&nbsp;', ' ').replace('&amp;', '&')
        
        results.append(
            SearchResult(
                title=title,
                url=url,
                description=description[:500] if description else None
            )
        )

    logger.debug(f'Found {len(results)} search results for: {search_phrase}')
    return results


@mcp.tool
async def read_documentation(
    ctx: Context,
    url: str = Field(description='URL of the OCI documentation page to read'),
    max_length: int = Field(
        default=5000,
        description='Maximum number of characters to return.',
        gt=0,
        lt=1000000,
    ),
    start_index: int = Field(
        default=0,
        description='On return output starting at this character index, useful if a previous fetch was truncated and more content is required.',
        ge=0,
    ),
) -> str:
    """Fetch and convert an OCI documentation page to markdown format.

    ## Usage

    This tool retrieves the content of an OCI documentation page and converts it to markdown format.
    For long documents, you can make multiple calls with different start_index values to retrieve
    the entire content in chunks.

    ## URL Requirements

    - Must be from the https://docs.oracle.com/ domain
    - Must end with .html or .htm

    ## Example URLs

    - https://docs.oracle.com/en-us/iaas/Content/Object/Concepts/objectstorageoverview.htm
    - https://docs.oracle.com/en-us/iaas/Content/Compute/References/bestpracticescompute.htm

    ## Output Format

    The output is formatted as markdown text with:
    - Preserved headings and structure
    - Code blocks for examples
    - Lists and tables converted to markdown format

    ## Handling Long Documents

    If the response indicates the document was truncated, you have several options:

    1. **Continue Reading**: Make another call with start_index set to the end of the previous response
    2. **Stop Early**: For very long documents (>30,000 characters), if you've already found the specific information needed, you can stop reading

    Args:
        ctx: MCP context for logging and error handling
        url: URL of the OCI documentation page to read
        max_length: Maximum number of characters to return
        start_index: On return output starting at this character index

    Returns:
        Markdown content of the OCI documentation
    """
    # Validate that URL is from docs.oracle.com and ends with .htm
    url_str = str(url)
    if not re.match(r'^https?://docs\.oracle\.com/', url_str):
        await ctx.error(f'Invalid URL: {url_str}. URL must be from the docs.oracle.com domain')
        raise ValueError('URL must be from the docs.oracle.com domain')
    if not url_str.endswith('.htm') and not url_str.endswith('.html'):
        await ctx.error(f'Invalid URL: {url_str}. URL must end with .htm or .html')
        raise ValueError('URL must end with .htm or .html')

    logger.debug(f'Fetching documentation from {url_str}')

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url_str,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
                timeout=30,
            )
        except httpx.HTTPError as e:
            error_msg = f'Failed to fetch {url_str}: {str(e)}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return error_msg

        if response.status_code >= 400:
            error_msg = f'Failed to fetch {url_str} - status code {response.status_code}'
            logger.error(error_msg)
            await ctx.error(error_msg)
            return error_msg
        response.encoding = 'utf-8'
        page_raw = response.text
        content_type = response.headers.get('content-type', '')

    if is_html_content(page_raw, content_type):
        content = extract_content_from_html(page_raw)
    else:
        content = page_raw

    result = format_documentation_result(url_str, content, start_index, max_length)

    # Log if content was truncated
    if len(content) > start_index + max_length:
        logger.debug(
            f'Content truncated at {start_index + max_length} of {len(content)} characters'
        )

    return result




def main():
    """Run the MCP server with CLI argument support."""
    parser = argparse.ArgumentParser(
        description='An OCI Labs Model Context Protocol (MCP) server for OCI Documentation'
    )
    parser.add_argument('--transport', type=str, default='streamable-http',
                        choices=['stdio', 'sse', 'streamable-http'],
                        help='Transport protocol to use (default: streamable-http)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind the server to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port to run the server on (default: 8000)')
    parser.add_argument('--path', type=str, default='/mcp',
                        help='Path for the MCP endpoint (default: /mcp)')

    args = parser.parse_args()

    logger.info('Starting OCI Documentation MCP Server')
    logger.info(f'Transport: {args.transport}')

    if args.transport == 'stdio':
        logger.info('Using stdio transport')
        mcp.run()
    elif args.transport == 'sse':
        logger.info(f'Using SSE transport on {args.host}:{args.port}')
        mcp.run(transport='sse', host=args.host, port=args.port)
    else:
        logger.info(f'Using Streamable HTTP transport on {args.host}:{args.port}{args.path}')
        mcp.run(transport='streamable-http', host=args.host, port=args.port, path=args.path)


if __name__ == '__main__':
    main()
