import jwt, datetime, os

# Try to import psycopg2-binary first, fall back to psycopg2 if not available
try:
    import psycopg2
except ImportError:
    try:
        import psycopg2.binary as psycopg2
    except ImportError:
        raise ImportError("Neither psycopg2 nor psycopg2-binary is installed. Please install one of them with: pip install psycopg2-binary")
from flask import Flask, request

# Import custom logger
from log.custom_logger import get_custom_logger

# Initialize Flask app
server = Flask(__name__)

# Set up logger
logger = get_custom_logger(service_name="auth-service")

def get_db_connection():
    host = os.getenv('DATABASE_HOST'),
    database = os.getenv('DATABASE_NAME'),
    user = os.getenv('DATABASE_USER'),
    password = os.getenv('DATABASE_PASSWORD'),
    port = 5432

    logger.info(f"Connecting to database", extra={
        'host': host[0],
        'database': database[0],
        'user': user[0],
        'port': port
    })

    try:
        conn = psycopg2.connect(host=os.getenv('DATABASE_HOST'),
                                database=os.getenv('DATABASE_NAME'),
                                user=os.getenv('DATABASE_USER'),
                                password=os.getenv('DATABASE_PASSWORD'),
                                port=5432)
        logger.info("Database connection established")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise


@server.route('/login', methods=['POST'])
def login():
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Login attempt", extra={'request_id': request_id})
    
    auth_table_name = os.getenv('AUTH_TABLE')
    auth = request.authorization
    
    if not auth or not auth.username or not auth.password:
        logger.warning("Missing authentication credentials", extra={
            'request_id': request_id,
            'has_auth': auth is not None,
            'has_username': auth.username if auth else None,
            'has_password': bool(auth.password) if auth else None
        })
        return 'Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = f"SELECT email, password FROM {auth_table_name} WHERE email = %s"
        
        logger.debug("Executing database query", extra={
            'request_id': request_id,
            'query': query,
            'username': auth.username
        })
        
        res = cur.execute(query, (auth.username,))
        
        if res is None:
            user_row = cur.fetchone()
            
            if user_row is None:
                logger.warning("User not found", extra={
                    'request_id': request_id,
                    'username': auth.username
                })
                return 'Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
                
            email = user_row[0]
            password = user_row[1]

            if auth.username != email or auth.password != password:
                logger.warning("Invalid credentials", extra={
                    'request_id': request_id,
                    'username': auth.username
                })
                return 'Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
            else:
                logger.info("Login successful", extra={
                    'request_id': request_id, 
                    'username': auth.username
                })
                return CreateJWT(auth.username, os.environ['JWT_SECRET'], True)
        else:
            logger.warning("Database query failed", extra={
                'request_id': request_id,
                'result': res
            })
            return 'Could not verify', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", extra={
            'request_id': request_id,
            'username': auth.username if auth else None
        })
        return 'Internal server error', 500

def CreateJWT(username, secret, authz):
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

@server.route('/validate', methods=['POST'])
def validate():
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Token validation request", extra={'request_id': request_id})
    
    # Check if Authorization header exists
    if 'Authorization' not in request.headers:
        logger.warning("Missing Authorization header", extra={'request_id': request_id})
        return 'Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
        
    encoded_jwt = request.headers['Authorization']
    
    if not encoded_jwt:
        logger.warning("Empty Authorization header", extra={'request_id': request_id})
        return 'Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}

    try:
        encoded_jwt = encoded_jwt.split(' ')[1]
        logger.debug("Decoding JWT", extra={'request_id': request_id})
        decoded_jwt = jwt.decode(encoded_jwt, os.environ['JWT_SECRET'], algorithms=["HS256"])
        
        logger.info("Token validated successfully", extra={
            'request_id': request_id,
            'username': decoded_jwt.get('username', 'unknown')
        })
        
        return decoded_jwt, 200
    except IndexError:
        logger.warning("Malformed Authorization header", extra={'request_id': request_id})
        return 'Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token", extra={'request_id': request_id})
        return 'Token expired', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}", extra={'request_id': request_id})
        return 'Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login required!"'}
    except Exception as e:
        logger.error(f"Validation exception: {str(e)}", extra={'request_id': request_id})
        return 'Internal server error', 500

if __name__ == '__main__':
    logger.info("Starting auth service", extra={
        'host': '0.0.0.0',
        'port': 5000
    })
    
    try:
        server.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.critical(f"Server crashed: {str(e)}")
