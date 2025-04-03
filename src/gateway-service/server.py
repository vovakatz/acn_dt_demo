import os, gridfs, pika, json
from fastapi import FastAPI, Request, Depends, HTTPException, File, UploadFile, Query, Header, Form, Cookie
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from auth import validate
from auth_svc import access
from storage import util
from bson.objectid import ObjectId
from typing import Optional, List, Dict, Any
import uvicorn
import io
from contextlib import asynccontextmanager # Added import

# Import custom logger
from log.custom_logger import get_custom_logger

# Set up logger
logger = get_custom_logger(service_name="gateway-service")

# Log initialization
logger.info("Initializing gateway service")

# MongoDB and RabbitMQ connections (will be initialized in lifespan)
mongo_video = None
mongo_mp3 = None
fs_videos = None
fs_mp3s = None
channel = None
connection = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_video, mongo_mp3, fs_videos, fs_mp3s, channel, connection
    logger.info("Lifespan startup: Initializing resources...")

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
        db_video = mongo_video.get_database() # Get default db
        db_mp3 = mongo_mp3.get_database()   # Get default db
        fs_videos = gridfs.GridFS(db_video)
        fs_mp3s = gridfs.GridFS(db_mp3)

        # Setup RabbitMQ connection
        logger.info("Connecting to RabbitMQ", extra={'host': 'rabbitmq'})
        # Ensure heartbeat is not disabled in production without understanding implications
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq", heartbeat=0))
        channel = connection.channel()

        logger.info("Lifespan startup: Resources initialized successfully")

        yield # Application runs here

    except Exception as e:
        logger.critical(f"Lifespan startup failed: {str(e)}")
        # Depending on the error, you might want to prevent the app from starting fully
        raise
    finally:
        # Shutdown logic: Clean up resources
        logger.info("Lifespan shutdown: Cleaning up resources...")
        if mongo_video:
            mongo_video.close()
            logger.info("MongoDB video connection closed.")
        if mongo_mp3:
            mongo_mp3.close()
            logger.info("MongoDB mp3 connection closed.")
        if connection and connection.is_open:
            connection.close()
            logger.info("RabbitMQ connection closed.")
        logger.info("Lifespan shutdown: Cleanup finished.")


# Initialize FastAPI app with lifespan
app = FastAPI(title="Gateway Service", lifespan=lifespan) # Updated initialization

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


# --- Removed @app.on_event("startup") and @app.on_event("shutdown") functions ---


@app.post("/login")
async def login_route(auth_result=Depends(access.login)):
    request_id = os.urandom(8).hex()  # Generate a unique request ID
    logger.info("Login request received", extra={'request_id': request_id})

    try:
        response, err = auth_result

        if not err:
            logger.info("Login successful", extra={'request_id': request_id})
            return JSONResponse(content=response)
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

# UI Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    # For the initial page load, we don't check the token server-side
    # The client-side JavaScript will handle authentication and API calls
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": {"username": "User"} # Default placeholder, will be replaced by client-side JS
    })

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    return response

# API endpoint to get user's files
@app.get("/api/files")
async def get_files(auth_result=Depends(validate.token)):
    request_id = os.urandom(8).hex()
    logger.info("Files list request received", extra={'request_id': request_id})

    try:
        # Validate token
        access_info, err = auth_result

        if err:
            logger.warning(f"Token validation failed: {err}", extra={'request_id': request_id})
            return JSONResponse(content=err[0], status_code=err[1])

        access_info = json.loads(access_info)
        username = access_info.get("username", "unknown")

        # Check admin status
        if access_info["admin"]:
            logger.info(f"User authorized for file listing", extra={
                'request_id': request_id,
                'username': username
            })

            # Get files from MongoDB
            # For MP3s (completed conversions)
            mp3_files = []
            for grid_out in fs_mp3s.find({}):
                file_data = {
                    "_id": str(grid_out._id),
                    "filename": grid_out.filename,
                    "uploadDate": grid_out.upload_date.isoformat(),
                    "status": "completed"
                }
                mp3_files.append(file_data)

            # For videos (pending or in-progress conversions)
            video_files = []
            for grid_out in fs_videos.find({}):
                # Check if this video has a corresponding MP3
                has_mp3 = any(mp3["filename"] == grid_out.filename for mp3 in mp3_files)

                if not has_mp3:
                    file_data = {
                        "_id": str(grid_out._id),
                        "filename": grid_out.filename,
                        "uploadDate": grid_out.upload_date.isoformat(),
                        "status": "processing"
                    }
                    video_files.append(file_data)

            # Combine and sort by upload date (newest first)
            all_files = mp3_files + video_files
            all_files.sort(key=lambda x: x["uploadDate"], reverse=True)

            return JSONResponse(content=all_files)
        else:
            logger.warning("Unauthorized files list attempt", extra={
                'request_id': request_id,
                'username': username
            })
            raise HTTPException(status_code=401, detail="not authorized")

    except Exception as e:
        logger.error(f"Files list exception: {str(e)}", extra={'request_id': request_id})
        raise HTTPException(status_code=500, detail="internal server error")

# API endpoint for login
@app.post("/api/login")
async def api_login(request: Request):
    request_id = os.urandom(8).hex()
    logger.info("API login request received", extra={'request_id': request_id})

    try:
        # Parse JSON body
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JSONResponse(content={"detail": "missing credentials"}, status_code=401)

        # Create credentials
        from fastapi.security import HTTPBasicCredentials
        credentials = HTTPBasicCredentials(username=username, password=password)

        # Call login function
        response, err = await access.login_with_credentials(credentials)

        if not err:
            logger.info("API login successful", extra={'request_id': request_id})
            return JSONResponse(content=response)
        else:
            logger.warning(f"API login failed: {err}", extra={'request_id': request_id})
            return JSONResponse(content={"detail": err[0]}, status_code=err[1])

    except Exception as e:
        logger.error(f"API login exception: {str(e)}", extra={'request_id': request_id})
        return JSONResponse(content={"detail": "internal server error"}, status_code=500)

if __name__ == "__main__":
    logger.info("Starting gateway service", extra={
        'host': '0.0.0.0',
        'port': 8080
    })

    try:
        uvicorn.run(app, host="0.0.0.0", port=8080)
    except Exception as e:
        logger.critical(f"Server crashed: {str(e)}")
