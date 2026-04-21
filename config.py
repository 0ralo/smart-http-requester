import os

DEBUG = os.environ.get("DEBUG", "False") == "True"

REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")


POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = os.environ.get("POSTGRES_HOST", "5432")
POSTGRES_DATABASE = os.environ.get("POSTGRES_DATABASE", "development")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "dev")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
