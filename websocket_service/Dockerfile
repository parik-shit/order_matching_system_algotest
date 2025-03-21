# websocket_service/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies required by the websocket service
RUN pip install fastapi uvicorn redis websockets

# Copy only the websocket service code from the websocket_service folder
COPY . .

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
