"""
FastAPI REST API server for MCP Obsidian.

Provides HTTP endpoints for all MCP tools with authentication,
rate limiting, and monitoring.
"""

import os
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp-api")

# Import MCP tools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.mcp_obsidian import tools, server as mcp_server
from .models import (
    ToolRequest,
    ToolResponse,
    ToolListResponse,
    ToolInfo,
    HealthResponse,
    TokenRequest,
    TokenResponse,
    ErrorResponse
)
from .auth import (
    verify_token,
    get_current_user,
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from .middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    ErrorHandlingMiddleware
)

# Create FastAPI app
app = FastAPI(
    title="MCP Obsidian API",
    description="REST API wrapper for MCP Obsidian server with semantic search capabilities",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (optional, for production)
trusted_hosts = os.getenv("TRUSTED_HOSTS", "").split(",")
if trusted_hosts and trusted_hosts[0]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=trusted_hosts
    )

# Custom middleware
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting
rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
app.add_middleware(RateLimitMiddleware, requests_per_minute=rate_limit_per_minute)

# Tool categories
TOOL_CATEGORIES = {
    "discovery": ["analyze_vault_structure", "analyze_frontmatter", "suggest_frontmatter", "get_folder_context"],
    "crud": [
        "create_person", "list_people", "update_person",
        "create_project", "list_projects", "list_companies",
        "create_daily_note", "append_to_daily", "get_recent_dailies"
    ],
    "semantic": [
        "semantic_search", "find_related_notes", "suggest_links",
        "analyze_relationships", "rebuild_embeddings"
    ],
    "core": [
        "list_files_in_vault", "list_files_in_dir", "get_file_contents",
        "search", "patch_content", "append_content", "put_content",
        "delete_file", "complex_search", "batch_get_file_contents",
        "periodic_notes", "recent_periodic_notes", "recent_changes"
    ]
}


def get_tool_category(tool_name: str) -> Optional[str]:
    """Get category for a tool."""
    # Remove obsidian_ prefix if present
    clean_name = tool_name.replace("obsidian_", "")

    for category, tools_list in TOOL_CATEGORIES.items():
        if clean_name in tools_list:
            return category
    return "other"


# ============================================================================
# Health and Info Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs."""
    return JSONResponse(
        content={
            "message": "MCP Obsidian API",
            "version": "0.3.0",
            "docs": "/docs",
            "health": "/health"
        }
    )


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and component health.
    """
    # Check MCP core
    mcp_healthy = len(mcp_server.tool_handlers) > 0

    # Check embeddings (if available)
    embeddings_healthy = True
    try:
        from src.mcp_obsidian.semantic import EmbeddingsManager
        manager = EmbeddingsManager()
        stats = manager.get_cache_stats()
        embeddings_healthy = stats is not None
    except Exception as e:
        logger.warning(f"Embeddings check failed: {e}")
        embeddings_healthy = False

    # Check Obsidian API
    obsidian_healthy = True
    try:
        from src.mcp_obsidian import obsidian
        api_key = os.getenv("OBSIDIAN_API_KEY", "")
        host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")
        if api_key:
            client = obsidian.Obsidian(api_key=api_key, host=host)
            # Simple check - list files
            client.list_files_in_vault()
    except Exception as e:
        logger.warning(f"Obsidian API check failed: {e}")
        obsidian_healthy = False

    overall_status = "healthy" if (mcp_healthy and obsidian_healthy) else "degraded"

    return HealthResponse(
        status=overall_status,
        version="0.3.0",
        timestamp=datetime.now(),
        components={
            "mcp_core": "healthy" if mcp_healthy else "unhealthy",
            "embeddings": "healthy" if embeddings_healthy else "unavailable",
            "obsidian_api": "healthy" if obsidian_healthy else "unhealthy"
        }
    )


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/token", response_model=TokenResponse, tags=["Authentication"])
async def login(token_request: TokenRequest):
    """
    Get JWT access token.

    Authenticate with username/password and receive a JWT token.
    """
    user = authenticate_user(token_request.username, token_request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "roles": user.get("roles", [])
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# ============================================================================
# Tools Endpoints
# ============================================================================

@app.get("/api/v1/tools", response_model=ToolListResponse, tags=["Tools"])
async def list_tools(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    List all available MCP tools.

    Returns information about all registered tools with their descriptions.
    """
    tools_list = []
    category_counts = {}

    for handler in mcp_server.tool_handlers.values():
        tool_desc = handler.get_tool_description()
        category = get_tool_category(handler.name)

        tools_list.append(
            ToolInfo(
                name=handler.name,
                description=tool_desc.description,
                category=category
            )
        )

        category_counts[category] = category_counts.get(category, 0) + 1

    return ToolListResponse(
        total=len(tools_list),
        tools=tools_list,
        categories=category_counts
    )


@app.post("/api/v1/tools/{tool_name}", response_model=ToolResponse, tags=["Tools"])
async def execute_tool(
    tool_name: str,
    request: ToolRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute a specific MCP tool.

    Args:
        tool_name: Name of the tool to execute
        request: Tool arguments

    Returns:
        Tool execution result
    """
    import time
    start_time = time.time()

    # Get tool handler
    handler = mcp_server.get_tool_handler(tool_name)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}"
        )

    # Execute tool
    try:
        logger.info(f"Executing tool: {tool_name} with args: {request.args}")
        result = handler.run_tool(request.args)

        execution_time = time.time() - start_time

        # Parse result
        result_data = None
        if result and len(result) > 0:
            result_text = result[0].text
            try:
                # Try to parse as JSON
                result_data = json.loads(result_text)
            except json.JSONDecodeError:
                # Return as plain text
                result_data = result_text

        logger.info(f"Tool {tool_name} executed successfully in {execution_time:.3f}s")

        return ToolResponse(
            success=True,
            tool_name=tool_name,
            result=result_data,
            execution_time=execution_time
        )

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Tool {tool_name} execution failed: {str(e)}", exc_info=True)

        return ToolResponse(
            success=False,
            tool_name=tool_name,
            error=str(e),
            execution_time=execution_time
        )


# ============================================================================
# Convenience Endpoints for Common Operations
# ============================================================================

@app.post("/api/v1/search/semantic", tags=["Search"])
async def semantic_search(
    query: str,
    top_k: int = 10,
    min_similarity: float = 0.0,
    folder: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Semantic search for notes.

    Convenience endpoint for obsidian_semantic_search tool.
    """
    handler = mcp_server.get_tool_handler("obsidian_semantic_search")
    if not handler:
        raise HTTPException(status_code=404, detail="Semantic search tool not available")

    try:
        result = handler.run_tool({
            "query": query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "folder": folder
        })
        return json.loads(result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notes/{filepath:path}/related", tags=["Notes"])
async def get_related_notes(
    filepath: str,
    top_k: int = 10,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get notes related to a specific note.

    Convenience endpoint for obsidian_find_related_notes tool.
    """
    handler = mcp_server.get_tool_handler("obsidian_find_related_notes")
    if not handler:
        raise HTTPException(status_code=404, detail="Related notes tool not available")

    try:
        result = handler.run_tool({
            "filepath": filepath,
            "top_k": top_k
        })
        return json.loads(result[0].text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("=" * 80)
    logger.info("MCP Obsidian API Server Starting")
    logger.info("=" * 80)
    logger.info(f"Version: 0.3.0")
    logger.info(f"Total tools available: {len(mcp_server.tool_handlers)}")
    logger.info(f"Rate limit: {rate_limit_per_minute} requests/minute")
    logger.info(f"CORS origins: {allowed_origins}")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("MCP Obsidian API Server Shutting Down")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Configuration from environment
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8000"))
    reload = os.getenv("SERVER_RELOAD", "false").lower() == "true"
    workers = int(os.getenv("SERVER_WORKERS", "1"))

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "src.api.server:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
        log_level="info"
    )
