"""
Pydantic models for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from datetime import datetime


class ToolRequest(BaseModel):
    """Request model for tool execution."""

    args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments as key-value pairs"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "args": {
                    "query": "machine learning projects",
                    "top_k": 10,
                    "min_similarity": 0.7
                }
            }
        }


class ToolResponse(BaseModel):
    """Response model for tool execution."""

    success: bool = Field(description="Whether the operation succeeded")
    tool_name: str = Field(description="Name of the executed tool")
    result: Optional[Any] = Field(default=None, description="Tool execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time: Optional[float] = Field(default=None, description="Execution time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "tool_name": "obsidian_semantic_search",
                "result": [
                    {
                        "filepath": "Projects/AI Assistant.md",
                        "similarity": 0.89,
                        "title": "AI Assistant"
                    }
                ],
                "error": None,
                "execution_time": 0.156
            }
        }


class ToolInfo(BaseModel):
    """Information about a tool."""

    name: str = Field(description="Tool name")
    description: str = Field(description="Tool description")
    category: Optional[str] = Field(default=None, description="Tool category")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "obsidian_semantic_search",
                "description": "Search for notes by semantic meaning",
                "category": "semantic"
            }
        }


class ToolListResponse(BaseModel):
    """Response model for tool listing."""

    total: int = Field(description="Total number of tools")
    tools: List[ToolInfo] = Field(description="List of available tools")
    categories: Optional[Dict[str, int]] = Field(
        default=None,
        description="Tool counts by category"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Optional[Dict[str, str]] = Field(
        default=None,
        description="Status of service components"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "0.3.0",
                "timestamp": "2025-10-25T19:30:00",
                "components": {
                    "mcp_core": "healthy",
                    "embeddings": "healthy",
                    "obsidian_api": "healthy"
                }
            }
        }


class TokenRequest(BaseModel):
    """Request model for token generation."""

    username: str = Field(description="Username")
    password: str = Field(description="Password")


class TokenResponse(BaseModel):
    """Response model for token generation."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Tool not found",
                "detail": "The requested tool 'invalid_tool' does not exist",
                "timestamp": "2025-10-25T19:30:00"
            }
        }
