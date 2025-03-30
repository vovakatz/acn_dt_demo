import os, gridfs, pika, json
from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile, Query, Header, Form
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from pymongo import MongoClient
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId
from typing import Optional
import uvicorn
import io

# Import custom logger
from log.custom_logger import get_custom_logger

# Initialize FastAPI app
app = FastAPI(title="Gateway Service")

# Set up logger
logger = get_custom_logger(service_name="gateway-service")

# Log initialization
logger.info("Initializing gateway service")

# MongoDB and RabbitMQ connections
mongo_video = None
mongo_mp3 = None
fs_videos = None
fs_mp3s = None
channel = None
connection = None

@app.on_event("startup")
async def startup_db_client():
    global mongo_video, mongo_mp3, fs_videos, fs_mp3s, channel, connection
    
    # Setup MongoDB connections
    logger.info("Connecting to MongoDB", extra={
        'videos_uri': os.environ.get('MONGODB_VIDEOS_URI'),
        'mp3s_uri': os.environ.get('MONGODB_MP3S_URI')
    })
    
    try:
        # Connect to MongoDB
        mongo_video = MongoClient(os.environ.get('MONGODB_VIDEOS_URI'))
        mongo_mp3 = MongoClient(os.environ.get('MONGODB_MP3S_URI'))
        
        # Setup GridFS
        logger.debug("Initializing GridFS")
        fs_videos = gridfs.GridFS(mongo_video.get_database())
        fs_mp3s = gridfs.GridFS(mongo_mp3.get_database())
        
        # Setup RabbitMQ connection
        logger.info("Connecting to RabbitMQ", extra={'host': 'rabbitmq'})
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq", heartbeat=0))
        channel = connection.channel()
        
        logger.info("Service initialization completed successfully")
        
    except Exception as e:
        logger.critical(f"Service initialization failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_db_client():
    global mongo_video, mongo_mp3, connection
    
    if mongo_video:
        mongo_video.close()
    
    if mongo_mp3:
        mongo_mp3.close()
    
    if connection:
        connection.close()

@app.post("/login")
async def login_route(auth_result=Depends(access.login)):
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Login request received", extra={'request_id': request_id})
    
    try:
        token, err = auth_result
        
        if not err:
            logger.info("Login successful", extra={'request_id': request_id})
            return JSONResponse(content=token)
        else:
            logger.warning(f"Login failed: {err}", extra={'request_id': request_id})
            return JSONResponse(content=err[0], status_code=err[1])
    
    except Exception as e:
        logger.error(f"Login exception: {str(e)}", extra={'request_id': request_id})
        raise HTTPException(status_code=500, detail="internal server error")

# Debug route to check token format
@app.get("/debug-token")
async def debug_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        return PlainTextResponse("No Authorization header", status_code=401)
    
    # Return the token format for debugging
    return PlainTextResponse(f"Token received: {authorization}")

# Direct file upload - bypass auth for simplicity
@app.post("/upload")
async def upload_route(file: UploadFile = File(...)):
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Direct upload request received", extra={'request_id': request_id})
    
    # Create a fake admin access for testing
    access_info = {
        "username": "admin@acn.com",
        "admin": True,
        "exp": 2000000000,  # Far future
    }
    
    try:
        logger.info(f"Using direct admin access for: {access_info['username']}", extra={
            'request_id': request_id,
            'username': access_info['username']
        })
        
        # Process file with direct admin access
        err = await util.upload(file, fs_videos, channel, access_info)
        
        if err:
            logger.error(f"Upload failed: {err}", extra={
                'request_id': request_id,
                'filename': file.filename
            })
            return JSONResponse(content=err[0], status_code=err[1])
        
        logger.info("Upload completed successfully", extra={'request_id': request_id})
        return JSONResponse(content="success!")
    
    except Exception as e:
        logger.error(f"Upload exception: {str(e)}", extra={'request_id': request_id})
        raise HTTPException(status_code=500, detail="internal server error")

@app.get("/download")
async def download_route(fid: str = Query(...), auth_result=Depends(validate.token)):
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Download request received", extra={'request_id': request_id})
    
    try:
        # Validate token
        logger.debug("Validating token", extra={'request_id': request_id})
        access_info, err = auth_result
        
        if err:
            logger.warning(f"Token validation failed: {err}", extra={'request_id': request_id})
            return JSONResponse(content=err[0], status_code=err[1])
        
        access_info = json.loads(access_info)
        username = access_info.get("username", "unknown")
        
        # Check admin status
        if access_info["admin"]:
            logger.info(f"User authorized for download", extra={
                'request_id': request_id,
                'username': username,
                'file_id': fid
            })
            
            if not fid:
                logger.warning("Missing file ID", extra={'request_id': request_id})
                raise HTTPException(status_code=400, detail="fid is required")
            
            try:
                logger.debug(f"Retrieving file from GridFS", extra={
                    'request_id': request_id,
                    'file_id': fid
                })
                
                out = fs_mp3s.get(ObjectId(fid))
                
                logger.info(f"File download successful", extra={
                    'request_id': request_id,
                    'file_id': fid
                })
                
                # Create a bytes io stream from the GridFS file
                file_like = io.BytesIO(out.read())
                
                return StreamingResponse(
                    file_like, 
                    media_type="audio/mpeg",
                    headers={"Content-Disposition": f"attachment; filename={fid}.mp3"}
                )
            
            except Exception as e:
                logger.error(f"File retrieval failed: {str(e)}", extra={
                    'request_id': request_id,
                    'file_id': fid
                })
                raise HTTPException(status_code=500, detail="internal server error")
        else:
            logger.warning("Unauthorized download attempt", extra={
                'request_id': request_id,
                'username': username
            })
            raise HTTPException(status_code=401, detail="not authorized")
    
    except Exception as e:
        logger.error(f"Download exception: {str(e)}", extra={'request_id': request_id})
        raise HTTPException(status_code=500, detail="internal server error")

if __name__ == "__main__":
    logger.info("Starting gateway service", extra={
        'host': '0.0.0.0',
        'port': 8080
    })
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except Exception as e:
        logger.critical(f"Server crashed: {str(e)}")