FROM python:3.14-alpine

WORKDIR /app

# Copy requirements list
COPY ../../pyproject.toml .

# Install requirements
RUN pip install --no-cache-dir -e .

# Copy app
COPY ../.. .

# Create logs directory
RUN mkdir -p logs

# Run app
#CMD ["python", "-m", "uvicorn", "application:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
CMD ["python", "-m", "granian", "--interface", "asgi", "application:app", "--workers", "2", "--host", "0.0.0.0", "--port", "8000"]
