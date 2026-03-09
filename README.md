*Inspired by: https://github.com/awslabs/mcp/tree/main/src/aws-documentation-mcp-server*

# OCI Documentation MCP Server

> **Forked from [jin38324/oci-documentation-mcp-server](https://github.com/jin38324/oci-documentation-mcp-server)**  
> Many thanks to the original author for the great work!

Model Context Protocol (MCP) server for OCI Documentation

This MCP server provides tools to search for content, and access OCI documentation.

## Features

- **Read Documentation**: Fetch and convert OCI documentation pages to markdown format
- **Search Documentation**: Search OCI documentation using Oracle Documentation Search API
- **Multiple Transport Modes**: Supports stdio, SSE, and Streamable HTTP transport protocols

## Prerequisites

### Installation Requirements

1. Install `uv` from [Astral](https://docs.astral.sh/uv/getting-started/installation/) or the [GitHub README](https://github.com/astral-sh/uv#installation)
2. Install Python 3.10 or newer using `uv python install 3.10` (or a more recent version)

## Installation

### Option 1: Streamable HTTP (Recommended for OpenWebUI, Cherry Studio, etc.)

```json
{
  "mcpServers": {
    "oci-documentation-mcp-server": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Option 2: stdio (For Cursor, Claude Desktop, etc.)

```json
{
  "mcpServers": {
    "oci-documentation-mcp-server": {
      "command": "uvx",
      "args": [
        "--from",
        "oci-documentation-mcp-server@latest",
        "python",
        "-m",
        "oci_documentation_mcp_server.server",
        "--transport",
        "stdio"
      ],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

Or the simpler version:

```json
{
  "mcpServers": {
    "oci-documentation-mcp-server": {
      "command": "uvx",
      "args": ["oci-documentation-mcp-server@latest", "--transport", "stdio"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Basic Usage

Example:
 - In Cursor ask: `Write a function to download files for OCI Object Storage.`

 ![Cursor_MCP](./image/Cursor_MCP.gif)

## Running the Server

### Local Development

```bash
# Install dependencies
make install

# Run with Streamable HTTP (default, port 8000)
make run

# Run with custom port
make run PORT=9000

# Run with stdio transport
make run-stdio

# Run with SSE transport
make run-sse
```

### Docker Deployment

```bash
# Build Docker image
make docker-build

# Run Docker container
make docker-run PORT=8000

# Stop container
make docker-stop
```

### Command Line Options

```bash
uv run oci_documentation_mcp_server --help

# Options:
#   --transport {stdio,sse,streamable-http}
#                         Transport protocol to use (default: streamable-http)
#   --host HOST           Host to bind the server to (default: 0.0.0.0)
#   --port PORT           Port to run the server on (default: 8000)
#   --path PATH           Path for the MCP endpoint (default: /mcp)
```

## Integration with OpenWebUI

OpenWebUI requires [mcpo](https://github.com/open-webui/mcpo) as a proxy to use MCP servers:

### Step 1: Start the MCP Server

```bash
make run PORT=8001
```

### Step 2: Run mcpo Proxy

```bash
pip install mcpo

mcpo --port 8000 --api-key "your-secret-key" \
  --server-type "streamable-http" \
  -- http://127.0.0.1:8001/mcp
```

### Step 3: Configure OpenWebUI

- Go to Settings → Tools/Functions
- Add new tool server
- URL: `http://localhost:8000`
- API Key: `your-secret-key`

## Tools

### read_documentation

Fetches an OCI documentation page and converts it to markdown format.

```python
read_documentation(url: str, max_length: int = 5000, start_index: int = 0) -> str
```

**Parameters:**
- `url`: URL of the OCI documentation page (must be from docs.oracle.com and end with .htm or .html)
- `max_length`: Maximum number of characters to return (default: 5000)
- `start_index`: Start index for pagination (default: 0)

### search_documentation

Searches OCI documentation using the Oracle Documentation Search API.

```python
search_documentation(search_phrase: str, limit: int = 3) -> list[SearchResult]
```

**Parameters:**
- `search_phrase`: Search phrase to use
- `limit`: Maximum number of results to return (1-10, default: 3)

**Returns:**
- List of `SearchResult` objects with `title`, `url`, and `description` fields

## Development

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Clean build artifacts
make clean
```

## License

Apache License 2.0
