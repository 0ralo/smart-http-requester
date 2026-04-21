import os

DEBUG = os.environ.get("DEBUG", "False") == "True"

REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")


POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = os.environ.get("POSTGRES_HOST", "5432")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "development")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "dev")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "")