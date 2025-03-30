# Common Logging Module

This module provides a standardized JSON logging mechanism for all services in the microservices application.

## Features

- Structured JSON logging format
- ISO timestamp format
- Service name identification
- Log levels (debug, info, warning, error, critical)
- Support for context data via the `extra` parameter
- Distributed tracing support with trace_id and span_id fields

## Installation

Add the following to your service's requirements.txt:

```
python-json-logger~=3.3.0
```

## Usage

### Basic Usage

```python
import sys
import os

# Add the src directory to the Python path to make the common module accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.common.logging.custom_logger import get_custom_logger

# Initialize the logger with the service name
logger = get_custom_logger(service_name="my-service")

# Log messages at different levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

### Adding Context Data

```python
# Log with additional context
logger.info("User logged in", extra={
    'user_id': '12345',
    'request_id': 'abc-123',
    'trace_id': '0af7651916cd43dd8448eb211c80319c',
    'span_id': 'b7ad6b7169203331'
})
```

### Logging Exceptions

```python
try:
    # Some code that might raise an exception
    result = 1 / 0
except Exception as e:
    logger.error(f"Exception: {str(e)}", extra={
        "exception_type": type(e).__name__,
        "request_id": "abc-123"
    })
```

## Environment Variables

The logger supports the following environment variables:

- `MICROSERVICE_NAME`: Sets the service name if not provided explicitly
- `LOG_LEVEL`: Sets the logging level (defaults to INFO)

## Output Format

Example JSON log output:

```json
{
  "timestamp": "2025-03-28T16:45:12.345678",
  "level": "INFO",
  "name": "my-service",
  "message": "User logged in",
  "service": "my-service",
  "user_id": "12345",
  "request_id": "abc-123",
  "trace_id": "0af7651916cd43dd8448eb211c80319c",
  "span_id": "b7ad6b7169203331"
}
```