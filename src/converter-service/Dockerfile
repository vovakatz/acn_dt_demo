FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends --no-install-suggests build-essential libpq-dev python3-dev ffmpeg && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app

# Install dependencies with correct versions first to avoid conflicts
RUN pip install --no-cache-dir typing-extensions>=4.8.0
RUN pip install --no-cache-dir "pymongo>=4.5.0,<5.0.0"
RUN pip install --no-cache-dir --requirement /app/requirements.txt
COPY . /app

CMD ["python", "consumer.py"]