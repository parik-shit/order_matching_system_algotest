# engine_service/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY wait-for-it.sh /app/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# Install dependencies required by the engine (including persistence packages)
RUN pip install redis sqlalchemy psycopg2-binary

# Copy only the engine service code from the engine_service folder
COPY . .

# Run the engine service
CMD ["python", "engine_service.py"]
