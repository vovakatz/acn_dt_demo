import os, requests, json
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

async def login_with_credentials(credentials: HTTPBasicCredentials):
    """Handle login with basic auth credentials"""
    if not credentials.username or not credentials.password:
        raise HTTPException(status_code=401, detail="missing credentials")

    basicAuth = (credentials.username, credentials.password)

    response = requests.post(
        f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/login", auth=basicAuth
    )

    if response.status_code == 200:
        try:
            # Try to parse JSON response
            json_response = response.json()
            return json_response, None
        except json.JSONDecodeError:
            # Fallback for legacy format (just in case)
            return {"token": response.text}, None
    else:
        return None, (response.text, response.status_code)

async def login(request: Request = None, credentials: HTTPBasicCredentials = Depends(security)):
    """Handle login request from either FastAPI Request or direct credentials"""
    return await login_with_credentials(credentials)