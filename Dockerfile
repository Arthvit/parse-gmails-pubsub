FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pubsub_service ./pubsub_service

ENV PYTHONPATH="/app/pubsub_service/"

EXPOSE 8080

CMD ["python", "pubsub_service/main.py"]