# order_service/Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies required by the order service (FastAPI, Uvicorn, Redis, etc.)
RUN pip install fastapi uvicorn redis pydantic

# Copy only the order service code from the order_service folder
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
