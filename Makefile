.PHONY: help install dev run run-stdio run-sse build docker-build docker-run docker-push clean test lint

help:
	@echo "OCI Documentation MCP Server - Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  install        Install dependencies using uv"
	@echo "  dev            Install development dependencies"
	@echo "  run            Run server with Streamable HTTP (default)"
	@echo "  run-stdio      Run server with stdio transport"
	@echo "  run-sse        Run server with SSE transport"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build Docker image"
	@echo "  docker-run     Run Docker container"
	@echo "  docker-push    Push Docker image to registry"
	@echo ""
	@echo "Quality:"
	@echo "  test           Run tests"
	@echo "  lint           Run linting and formatting"
	@echo "  clean          Clean build artifacts"

install:
	uv sync

dev:
	uv sync --all-groups

PORT ?= 8000
HOST ?= 0.0.0.0

run:
	uv run oci_documentation_mcp_server --transport streamable-http --host $(HOST) --port $(PORT) --path /mcp

run-stdio:
	uv run oci_documentation_mcp_server --transport stdio

run-sse:
	uv run oci_documentation_mcp_server --transport sse --host $(HOST) --port $(PORT)

IMAGE_NAME ?= oci-documentation-mcp-server
IMAGE_TAG ?= latest
REGISTRY ?= 

docker-build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run:
	docker run -d --name oci-documentation-mcp-server \
		-p $(PORT):8000 \
		-e FASTMCP_LOG_LEVEL=INFO \
		$(IMAGE_NAME):$(IMAGE_TAG)

docker-push:
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

docker-stop:
	docker stop oci-documentation-mcp-server || true
	docker rm oci-documentation-mcp-server || true

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} +
