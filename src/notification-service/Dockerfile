FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests build-essential libpq-dev python3-dev ffmpeg  \
    && pip install --no-cache-dir --upgrade pip

WORKDIR /app
RUN mkdir -p /app/src/notification-service /app/src/common

COPY notification-service/requirements.txt /app/src/notification-service/

RUN pip install --no-cache-dir --requirement /app/src/notification-service/requirements.txt

COPY common /app/src/common
COPY notification-service/. /app/src/notification-service

ENV PYTHONPATH=/app

WORKDIR /app/src/notification-service

CMD ["python", "consumer.py"]