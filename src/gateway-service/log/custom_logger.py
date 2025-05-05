import logging
import datetime
import os
from pythonjsonlogger import jsonlogger
import logging.config # Added

# Keep track of configured loggers to avoid re-configuring
_configured_loggers = set() # Added

# --- Logging Configuration ---
# Define logging config using dictConfig schema
# Note: service_name will be populated dynamically in configure_logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "custom_json": {
            "()": "log.custom_logger.CustomJsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s",
            "service_name": None, # Placeholder
        },
        "access": {
            "()": "log.custom_logger.CustomJsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s",
            "service_name": None, # Placeholder
        },
    },
    "handlers": {
        "default": {
            "formatter": "custom_json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": { # Root logger
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        # Service-specific logger added dynamically
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

def configure_logging(service_name="unknown-service"):
    """Configure logging using dictConfig."""
    if service_name in _configured_loggers:
        return # Already configured

    # Dynamically set service_name in formatters and add service logger
    LOGGING_CONFIG["formatters"]["custom_json"]["service_name"] = service_name
    LOGGING_CONFIG["formatters"]["access"]["service_name"] = service_name
    LOGGING_CONFIG["loggers"][service_name] = {
        "handlers": ["default"],
        "level": "INFO",
        "propagate": False,
    }

    logging.config.dictConfig(LOGGING_CONFIG)
    _configured_loggers.add(service_name)
    # Optional: Log that configuration happened
    # logging.getLogger(service_name).debug(f"Logging configured for service: {service_name}")


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
    
    # Configure logging for this service if not already done
    # This will set up handlers and formatters via dictConfig
    configure_logging(service_name)

    # Return the logger instance (already configured by dictConfig)
    return logging.getLogger(service_name)


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
