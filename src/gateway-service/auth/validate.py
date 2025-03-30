import os, requests, json, logging
from fastapi import Request, HTTPException, Depends, Header
from typing import Optional, Tuple, Any, Dict, Union

# Create a logger for debugging
logger = logging.getLogger("validate")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)

async def get_token(authorization: Optional[str] = Header(None)):
    """Extract token from authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="missing credentials")
    return authorization

async def token(request: Request = None, authorization: str = Depends(get_token)) -> Tuple[Optional[str], Optional[Tuple[str, int]]]:
    """Validate token with auth service"""
    if not authorization:
        logger.error("No authorization header provided")
        return None, ("missing credentials", 401)
    
    # Log the token for debugging (first 10 chars only for security)
    safe_token = authorization[:10] + "..." if authorization else "None"
    logger.debug(f"Token received: {safe_token}")
    
    try:
        # Forward token as-is to auth service
        logger.debug(f"Sending token to auth service")
        response = requests.post(
            f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/validate",
            headers={"Authorization": authorization},
        )
        
        logger.debug(f"Auth service response: {response.status_code}")
        
        if response.status_code == 200:
            try:
                logger.debug("Token validated successfully")
                return response.text, None
            except Exception as e:
                logger.error(f"Error parsing auth response: {e}")
                return None, (f"error parsing auth response: {e}", 500)
        else:
            logger.warning(f"Auth validation failed: {response.status_code} {response.text}")
            return None, (response.text, response.status_code)
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return None, (f"error validating token: {e}", 500)