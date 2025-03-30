import logging
import datetime
import os
from pythonjsonlogger import jsonlogger


def get_custom_logger(service_name=None):
    """
    Create and configure a custom JSON logger.
    
    Args:
        service_name (str, optional): The name of the service to be included in log records.
            If not provided, it attempts to get the service name from the MICROSERVICE_NAME
            environment variable, or defaults to 'unknown-service'.
    
    Returns:
        logging.Logger: A configured logger instance.
    """
    # Get service name from environment variable if not provided
    if service_name is None:
        service_name = os.environ.get("MICROSERVICE_NAME", "unknown-service")
    
    # Create logger
    logger = logging.getLogger(service_name)
    
    # Only add handlers if the logger doesn't already have any
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create handler
        handler = logging.StreamHandler()
        
        # Create formatter
        formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s', service_name=service_name)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Create formatter
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, service_name=None, **kwargs):
        super(CustomJsonFormatter, self).__init__(*args, **kwargs)
        self.service_name = service_name
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.datetime.now().isoformat()
        log_record['level'] = record.levelname
        
        # Add service name
        log_record['service'] = self.service_name or record.name
        
        # Add trace context if available
        if hasattr(record, 'trace_id'):
            log_record['trace_id'] = record.trace_id
        if hasattr(record, 'span_id'):
            log_record['span_id'] = record.span_id
        
        # Add additional context from extra fields
        for key, value in getattr(record, '__dict__', {}).items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
                          'trace_id', 'span_id') and not key.startswith('_'):
                log_record[key] = value


# Example usage
# logger = get_custom_logger('my-service')
# logger.info("User logged in", extra={
#     'user_id': '12345',
#     'request_id': 'abc-123',
#     'trace_id': '0af7651916cd43dd8448eb211c80319c',
#     'span_id': 'b7ad6b7169203331'
# })