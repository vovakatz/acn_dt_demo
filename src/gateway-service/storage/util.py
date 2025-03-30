import pika, json, os, sys

# Use the local logger import
from ..log.custom_logger import get_custom_logger

# Initialize logger
logger = get_custom_logger(service_name="gateway-storage")

def upload(f, fs, channel, access):
    username = access.get("username", "unknown")
    request_id = os.urandom(8).hex()  # Generate a unique request ID for this upload
    
    logger.info("Starting file upload", extra={
        'request_id': request_id,
        'username': username,
        'filename': getattr(f, 'filename', 'unknown')
    })
    
    try:
        logger.debug("Saving file to GridFS", extra={'request_id': request_id})
        fid = fs.put(f)
        
        logger.info("File saved to GridFS", extra={
            'request_id': request_id,
            'file_id': str(fid)
        })
        
    except Exception as err:
        logger.error(f"Failed to save file to GridFS: {str(err)}", extra={
            'request_id': request_id,
            'error': str(err)
        })
        return "internal server error, fs level", 500

    # Prepare message for video processing queue
    message = {
        "video_fid": str(fid),
        "mp3_fid": None,
        "username": username,
    }

    try:
        logger.info("Publishing message to video queue", extra={
            'request_id': request_id,
            'file_id': str(fid),
            'queue': 'video'
        })
        
        channel.basic_publish(
            exchange="",
            routing_key="video",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        
        logger.info("Message published successfully", extra={
            'request_id': request_id,
            'file_id': str(fid)
        })
        
        return None
        
    except Exception as err:
        logger.error(f"Failed to publish message to queue: {str(err)}", extra={
            'request_id': request_id,
            'file_id': str(fid),
            'error': str(err)
        })
        
        # Cleanup: delete the file if message publishing fails
        logger.debug(f"Cleaning up file from GridFS after queue error", extra={
            'request_id': request_id,
            'file_id': str(fid)
        })
        fs.delete(fid)
        
        return f"internal server error rabbitmq issue, {err}", 500
