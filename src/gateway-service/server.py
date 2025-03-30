import os, gridfs, pika, json
from flask import Flask, request, send_file
from flask_pymongo import PyMongo
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId

# Import custom logger
from log.custom_logger import get_custom_logger

# Initialize Flask app
server = Flask(__name__)

# Set up logger
logger = get_custom_logger(service_name="gateway-service")

# Log initialization
logger.info("Initializing gateway service")

# Setup MongoDB connections
logger.info("Connecting to MongoDB", extra={
    'videos_uri': os.environ.get('MONGODB_VIDEOS_URI'),
    'mp3s_uri': os.environ.get('MONGODB_MP3S_URI')
})

try:
    mongo_video = PyMongo(server, uri=os.environ.get('MONGODB_VIDEOS_URI'))
    mongo_mp3 = PyMongo(server, uri=os.environ.get('MONGODB_MP3S_URI'))
    
    # Setup GridFS
    logger.debug("Initializing GridFS")
    fs_videos = gridfs.GridFS(mongo_video.db)
    fs_mp3s = gridfs.GridFS(mongo_mp3.db)
    
    # Setup RabbitMQ connection
    logger.info("Connecting to RabbitMQ", extra={'host': 'rabbitmq'})
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq", heartbeat=0))
    channel = connection.channel()
    
    logger.info("Service initialization completed successfully")
    
except Exception as e:
    logger.critical(f"Service initialization failed: {str(e)}")
    raise

@server.route("/login", methods=["POST"])
def login():
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Login request received", extra={'request_id': request_id})
    
    try:
        token, err = access.login(request)
        
        if not err:
            logger.info("Login successful", extra={'request_id': request_id})
            return token
        else:
            logger.warning(f"Login failed: {err}", extra={'request_id': request_id})
            return err
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", extra={'request_id': request_id})
        return "internal server error", 500

@server.route("/upload", methods=["POST"])
def upload():
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Upload request received", extra={'request_id': request_id})
    
    try:
        # Validate token
        logger.debug("Validating token", extra={'request_id': request_id})
        access_info, err = validate.token(request)
        
        if err:
            logger.warning(f"Token validation failed: {err}", extra={'request_id': request_id})
            return err
        
        access_info = json.loads(access_info)
        username = access_info.get("username", "unknown")
        
        # Check admin status
        if access_info["admin"]:
            logger.info(f"User authorized for upload", extra={
                'request_id': request_id,
                'username': username
            })
            
            # Validate file count
            if len(request.files) != 1:
                logger.warning("Invalid file count", extra={
                    'request_id': request_id,
                    'file_count': len(request.files)
                })
                return "exactly 1 file required", 400
            
            # Process file
            for file_name, f in request.files.items():
                logger.info(f"Processing file", extra={
                    'request_id': request_id,
                    'filename': file_name
                })
                
                err = util.upload(f, fs_videos, channel, access_info)
                
                if err:
                    logger.error(f"Upload failed: {err}", extra={
                        'request_id': request_id,
                        'filename': file_name
                    })
                    return err
                
            logger.info("Upload completed successfully", extra={'request_id': request_id})
            return "success!", 200
        else:
            logger.warning("Unauthorized upload attempt", extra={
                'request_id': request_id,
                'username': username
            })
            return "not authorized", 401
    except Exception as e:
        logger.error(f"Upload exception: {str(e)}", extra={'request_id': request_id})
        return "internal server error", 500

@server.route("/download", methods=["GET"])
def download():
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Download request received", extra={'request_id': request_id})
    
    try:
        # Validate token
        logger.debug("Validating token", extra={'request_id': request_id})
        access_info, err = validate.token(request)
        
        if err:
            logger.warning(f"Token validation failed: {err}", extra={'request_id': request_id})
            return err
        
        access_info = json.loads(access_info)
        username = access_info.get("username", "unknown")
        
        # Check admin status
        if access_info["admin"]:
            # Get file ID
            fid_string = request.args.get("fid")
            
            logger.info(f"User authorized for download", extra={
                'request_id': request_id,
                'username': username,
                'file_id': fid_string
            })
            
            if not fid_string:
                logger.warning("Missing file ID", extra={'request_id': request_id})
                return "fid is required", 400
            
            try:
                logger.debug(f"Retrieving file from GridFS", extra={
                    'request_id': request_id,
                    'file_id': fid_string
                })
                
                out = fs_mp3s.get(ObjectId(fid_string))
                
                logger.info(f"File download successful", extra={
                    'request_id': request_id,
                    'file_id': fid_string
                })
                
                return send_file(out, download_name=f"{fid_string}.mp3")
            except Exception as e:
                logger.error(f"File retrieval failed: {str(e)}", extra={
                    'request_id': request_id,
                    'file_id': fid_string
                })
                return "internal server error", 500
        else:
            logger.warning("Unauthorized download attempt", extra={
                'request_id': request_id,
                'username': username
            })
            return "not authorized", 401
    except Exception as e:
        logger.error(f"Download exception: {str(e)}", extra={'request_id': request_id})
        return "internal server error", 500

if __name__ == "__main__":
    logger.info("Starting gateway service", extra={
        'host': '0.0.0.0',
        'port': 8080
    })
    
    try:
        server.run(host="0.0.0.0", port=8080)
    except Exception as e:
        logger.critical(f"Server crashed: {str(e)}")
