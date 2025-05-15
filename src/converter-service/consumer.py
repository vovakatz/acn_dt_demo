import pika, sys, os
from pymongo import MongoClient
import gridfs
from convert import to_mp3

# Import custom logger
from src.common.log.custom_logger import get_custom_logger

# Initialize logger
logger = get_custom_logger(service_name="converter-service")

def main():
    logger.info("Initializing converter service")
    
    try:
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGODB_URI')
        logger.info(f"Connecting to MongoDB", extra={'uri': mongo_uri})
        
        client = MongoClient(mongo_uri)
        db_videos = client.videos
        db_mp3s = client.mp3s
        
        # Initialize GridFS
        logger.debug("Initializing GridFS")
        fs_videos = gridfs.GridFS(db_videos)
        fs_mp3s = gridfs.GridFS(db_mp3s)
        
        # Connect to RabbitMQ
        logger.info("Connecting to RabbitMQ", extra={'host': 'rabbitmq'})
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='rabbitmq', heartbeat=0)
        )
        channel = connection.channel()
        
        def callback(ch, method, properties, body):
            message_id = method.delivery_tag
            logger.info(f"Received message from queue", extra={
                'message_id': message_id,
                'queue': os.environ.get("VIDEO_QUEUE")
            })
            
            err = to_mp3.start(body, fs_videos, fs_mp3s, ch, logger)
            
            if err:
                logger.error(f"Failed to process message: {err}", extra={
                    'message_id': message_id
                })
                ch.basic_nack(delivery_tag=message_id)
            else:
                logger.info("Successfully processed message", extra={
                    'message_id': message_id
                })
                ch.basic_ack(delivery_tag=message_id)
        
        video_queue = os.environ.get("VIDEO_QUEUE")
        logger.info(f"Setting up consumer for queue", extra={'queue': video_queue})
        
        channel.basic_consume(
            queue=video_queue, on_message_callback=callback
        )
        
        logger.info("Waiting for messages. To exit press CTRL+C")
        channel.start_consuming()
        
    except Exception as e:
        logger.critical(f"Service initialization failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}")
        sys.exit(1)
