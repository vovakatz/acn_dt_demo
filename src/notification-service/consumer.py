import pika, sys, os
from send import email
from src.common.log.custom_logger import get_custom_logger

def main(logger):
    # rabbitmq connection
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq",heartbeat=0))
    channel = connection.channel()

    def callback(ch, method, properties, body):
        logger.info(f"Processing message: {body}", extra={'message_id': method.delivery_tag})
        try:
            email.notification(logger, body)
            logger.info(f"Successfully processed message", extra={'message_id': method.delivery_tag})
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"Exception processing message: {str(e)}", extra={'message_id': method.delivery_tag})
            ch.basic_nack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=os.environ.get("MP3_QUEUE"), on_message_callback=callback
    )

    logger.info("Waiting for messages.")
    channel.start_consuming()

if __name__ == "__main__":
    logger = get_custom_logger(service_name="notification-service")

    try:
        logger.info("Starting notification service")
        main(logger)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)