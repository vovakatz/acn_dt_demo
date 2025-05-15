FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests build-essential libpq-dev python3-dev && pip install --no-cache-dir --upgrade pip

WORKDIR /app
RUN mkdir -p /app/src/gateway-service /app/src/common

COPY gateway-service/requirements.txt /app/src/gateway-service/

# Install dependencies with correct versions first to avoid conflicts
RUN pip install --no-cache-dir typing-extensions>=4.8.0 annotated-types>=0.6.0
RUN pip install --no-cache-dir "pymongo>=4.5.0,<5.0.0"
RUN pip install --no-cache-dir motor==3.3.2
RUN pip install --no-cache-dir --requirement /app/src/gateway-service/requirements.txt

COPY common /app/src/common
COPY gateway-service/. /app/src/gateway-service

EXPOSE 8080

ENV PYTHONPATH=/app

WORKDIR /app/src/gateway-service

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]