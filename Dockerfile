FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

COPY oci_documentation_mcp_server ./oci_documentation_mcp_server

EXPOSE 8000

ENV FASTMCP_LOG_LEVEL=INFO

CMD ["uv", "run", "oci_documentation_mcp_server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000", "--path", "/mcp"]
