FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests build-essential libpq-dev python3-dev && pip install --no-cache-dir --upgrade pip

# Create the same directory structure as local development
WORKDIR /app
RUN mkdir -p /app/src/auth-service /app/src/common

# Copy requirements and install dependencies
COPY auth-service/requirements.txt /app/src/auth-service/

# Install dependencies with correct versions first to avoid conflicts
RUN pip install --no-cache-dir typing-extensions>=4.8.0 annotated-types>=0.6.0
RUN pip install --no-cache-dir --requirement /app/src/auth-service/requirements.txt

# Copy the source code
COPY common /app/src/common
COPY auth-service/. /app/src/auth-service

EXPOSE 5000

# Set PYTHONPATH to include /app so imports work correctly
ENV PYTHONPATH=/app

# Change to the auth-service directory
WORKDIR /app/src/auth-service

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]