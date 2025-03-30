import jwt, datetime, os, logging
from typing import Optional, Dict, Any, Tuple, List
import asyncpg

from fastapi import FastAPI, Depends, HTTPException, Header, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

# Import custom logger
from log.custom_logger import get_custom_logger

# Setup console logging (only for debugging)
logging.basicConfig(level=logging.DEBUG)

# Initialize FastAPI app
app = FastAPI(title="Auth Service")

# Set up logger
logger = get_custom_logger(service_name="auth-service")

# Set up HTTP Basic Auth
security = HTTPBasic()

# Database pool
db_pool = None

@app.on_event("startup")
async def startup_db_client():
    global db_pool
    
    host = os.getenv('DATABASE_HOST')
    database = os.getenv('DATABASE_NAME')
    user = os.getenv('DATABASE_USER')
    password = os.getenv('DATABASE_PASSWORD')
    port = 5432

    logger.info(f"Connecting to database", extra={
        'host': host,
        'database': database,
        'user': user,
        'port': port
    })
    
    try:
        # Create a connection pool
        db_pool = await asyncpg.create_pool(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            min_size=5,
            max_size=20
        )
        logger.info("Database connection pool established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    global db_pool
    
    if db_pool:
        await db_pool.close()
        logger.debug("Database connection pool closed")

def create_jwt(username: str, secret: str, authz: bool) -> str:
    """Create a JWT token"""
    return jwt.encode(
        {
            "username": username,
            "exp": datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(days=1),
            "iat": datetime.datetime.now(tz=datetime.timezone.utc),
            "admin": authz,
        },
        secret,
        algorithm="HS256",
    )

@app.post('/login')
async def login(credentials: HTTPBasicCredentials = Depends(security)):
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Login attempt", extra={'request_id': request_id})
    
    auth_table_name = os.getenv('AUTH_TABLE')
    
    if not credentials or not credentials.username or not credentials.password:
        logger.warning("Missing authentication credentials", extra={
            'request_id': request_id,
            'has_credentials': credentials is not None,
            'has_username': credentials.username if credentials else None,
            'has_password': bool(credentials.password) if credentials else None
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify",
            headers={"WWW-Authenticate": "Basic realm=\"Login required!\""},
        )

    try:
        # Get a connection from the pool
        async with db_pool.acquire() as conn:
            query = f"SELECT email, password FROM {auth_table_name} WHERE email = $1"
            
            logger.debug("Executing database query", extra={
                'request_id': request_id,
                'query': query,
                'username': credentials.username
            })
            
            # Execute the query
            user_row = await conn.fetchrow(query, credentials.username)
            
            if user_row is None:
                logger.warning("User not found", extra={
                    'request_id': request_id,
                    'username': credentials.username
                })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not verify",
                    headers={"WWW-Authenticate": "Basic realm=\"Login required!\""},
                )
                
            email = user_row['email']
            password = user_row['password']

            if credentials.username != email or credentials.password != password:
                logger.warning("Invalid credentials", extra={
                    'request_id': request_id,
                    'username': credentials.username
                })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not verify",
                    headers={"WWW-Authenticate": "Basic realm=\"Login required!\""},
                )
            else:
                logger.info("Login successful", extra={
                    'request_id': request_id, 
                    'username': credentials.username
                })
                jwt_token = create_jwt(credentials.username, os.environ['JWT_SECRET'], True)
                return {"token": jwt_token, "message": "Login successful"}

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", extra={
            'request_id': request_id,
            'username': credentials.username if credentials else None
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Debug endpoint
@app.get('/debug-auth')
def debug_auth(authorization: Optional[str] = Header(None)):
    return PlainTextResponse(f"Auth header received: {authorization}")

@app.post('/validate')
async def validate(authorization: Optional[str] = Header(None)):
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Token validation request", extra={'request_id': request_id})
    
    # Debug log the authorization header
    logging.debug(f"Authorization header: {authorization}")
    
    # Check if Authorization header exists
    if not authorization:
        logger.warning("Missing Authorization header", extra={'request_id': request_id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=\"Login required!\""},
        )

    try:
        # Extract the token - handle both with and without "Bearer " prefix
        if authorization.startswith('Bearer '):
            encoded_jwt = authorization[7:]  # Remove "Bearer " prefix
        else:
            encoded_jwt = authorization
            
        logging.debug(f"Token to validate: {encoded_jwt[:20]}...")
        
        # Now validate the JWT token
        decoded_jwt = jwt.decode(encoded_jwt, os.environ['JWT_SECRET'], algorithms=["HS256"])
        
        logger.info("Token validated successfully", extra={
            'request_id': request_id,
            'username': decoded_jwt.get('username', 'unknown')
        })
        
        return decoded_jwt
        
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token", extra={'request_id': request_id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Basic realm=\"Login required!\""},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}", extra={'request_id': request_id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm=\"Login required!\""},
        )
    except Exception as e:
        logger.error(f"Validation exception: {str(e)}", extra={'request_id': request_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

if __name__ == '__main__':
    logger.info("Starting auth service", extra={
        'host': '0.0.0.0',
        'port': 5000
    })
    
    try:
        uvicorn.run(app, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.critical(f"Server crashed: {str(e)}")