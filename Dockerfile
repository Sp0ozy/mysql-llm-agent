FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# flush print() to docker logs immediately
ENV PYTHONUNBUFFERED=1
# skip .pyc files inside the container
ENV PYTHONDONTWRITEBYTECODE=1
