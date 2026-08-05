import os
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger("smart_sanitation_backend")

# REQ-SEC-1: Verify x-api-key custom header
API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key: Optional[str] = Security(api_key_header)):
    """
    Validates the custom HTTP header 'x-api-key'.
    Returns 401 Unauthorized for invalid or missing API keys.
    """
    expected_key = os.environ.get("API_SECRET_KEY")
    if not expected_key:
        logger.warning("API_SECRET_KEY is not set in environment variables. Failing secure.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API authentication not configured on server"
        )
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return api_key
