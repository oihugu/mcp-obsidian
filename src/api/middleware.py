"""
Middleware for request processing, rate limiting, and logging.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response
        """
        start_time = time.time()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add custom headers
            response.headers["X-Process-Time"] = str(process_time)

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} "
                f"- Duration: {process_time:.3f}s "
                f"- Client: {request.client.host if request.client else 'unknown'}"
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} "
                f"- Duration: {process_time:.3f}s"
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Note: For production with multiple instances, use Redis-based rate limiting.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI app
            requests_per_minute: Maximum requests per minute per client
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self.cleanup_interval = 60  # Cleanup every 60 seconds
        self.last_cleanup = datetime.now()

    def _cleanup_old_requests(self):
        """Remove old request records."""
        now = datetime.now()
        if (now - self.last_cleanup).total_seconds() > self.cleanup_interval:
            cutoff = now - timedelta(minutes=1)
            for client_id in list(self.requests.keys()):
                self.requests[client_id] = [
                    req_time for req_time in self.requests[client_id]
                    if req_time > cutoff
                ]
                if not self.requests[client_id]:
                    del self.requests[client_id]
            self.last_cleanup = now

    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier.

        Args:
            request: Incoming request

        Returns:
            Client identifier
        """
        # Try to get client IP
        if request.client:
            return request.client.host

        # Fallback to forwarded header (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        return "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Cleanup old requests periodically
        self._cleanup_old_requests()

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        # Get recent requests
        recent_requests = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]

        if len(recent_requests) >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for client {client_id}: "
                f"{len(recent_requests)} requests in last minute"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )

        # Record this request
        self.requests[client_id].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_id])
        )

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for consistent error handling."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Handle errors consistently.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response or error response
        """
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}", exc_info=True)

            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": str(e) if logger.level == logging.DEBUG else "An unexpected error occurred",
                    "timestamp": datetime.now().isoformat()
                }
            )
