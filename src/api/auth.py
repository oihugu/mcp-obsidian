"""
Authentication and authorization module.

Supports both JWT tokens and API keys for authentication.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

logger = logging.getLogger(__name__)

# Configuration from environment
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-PLEASE")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# API Keys from environment (comma-separated)
API_KEYS_STR = os.getenv("API_KEYS", "")
API_KEYS = set(key.strip() for key in API_KEYS_STR.split(",") if key.strip())

# Simple user database (in production, use proper database)
USERS_DB = {
    "admin": {
        "username": "admin",
        "password": os.getenv("ADMIN_PASSWORD", "changeme"),  # Should be hashed in production
        "roles": ["admin"]
    }
}

security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise AuthenticationError("Token has expired")

        return payload

    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise AuthenticationError("Invalid token")
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        raise AuthenticationError("Could not validate credentials")


def verify_api_key(api_key: str) -> bool:
    """
    Verify if API key is valid.

    Args:
        api_key: API key to verify

    Returns:
        True if valid, False otherwise
    """
    if not API_KEYS:
        logger.warning("No API keys configured!")
        return False

    return api_key in API_KEYS


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Verify authentication token (JWT or API key).

    Args:
        credentials: HTTP bearer credentials

    Returns:
        User information dict

    Raises:
        AuthenticationError: If authentication fails
    """
    token = credentials.credentials

    # Try API key first
    if verify_api_key(token):
        logger.info("Authentication successful via API key")
        return {
            "auth_type": "api_key",
            "authenticated": True,
            "roles": ["api_user"]
        }

    # Try JWT token
    try:
        payload = decode_token(token)
        logger.info(f"Authentication successful via JWT for user: {payload.get('sub')}")
        return {
            "auth_type": "jwt",
            "authenticated": True,
            "username": payload.get("sub"),
            "roles": payload.get("roles", []),
            "payload": payload
        }
    except AuthenticationError:
        raise

    raise AuthenticationError("Invalid authentication credentials")


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with username and password.

    Args:
        username: Username
        password: Password (should be hashed in production)

    Returns:
        User dict if authenticated, None otherwise
    """
    user = USERS_DB.get(username)

    if not user:
        return None

    # In production, use proper password hashing (bcrypt, argon2, etc.)
    if password != user["password"]:
        return None

    return user


def get_current_user(auth_data: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get current authenticated user.

    Args:
        auth_data: Authentication data from verify_token

    Returns:
        User information dict
    """
    return auth_data


def require_role(required_role: str):
    """
    Dependency to require specific role.

    Args:
        required_role: Required role name

    Returns:
        Dependency function
    """
    async def role_checker(auth_data: Dict[str, Any] = Depends(get_current_user)):
        roles = auth_data.get("roles", [])
        if required_role not in roles and "admin" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return auth_data

    return role_checker


# Logging configuration
if SECRET_KEY == "your-secret-key-change-in-production-PLEASE":
    logger.warning(
        "⚠️  WARNING: Using default JWT secret key! "
        "Set JWT_SECRET_KEY environment variable in production!"
    )

if not API_KEYS:
    logger.warning(
        "⚠️  WARNING: No API keys configured! "
        "Set API_KEYS environment variable for API key authentication."
    )

if USERS_DB["admin"]["password"] == "changeme":
    logger.warning(
        "⚠️  WARNING: Using default admin password! "
        "Set ADMIN_PASSWORD environment variable in production!"
    )
