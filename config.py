from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_use_ssl: bool = False
    redis_ca_cert: str | None = "/certs/ca.crt"
    redis_cert: str | None = "/certs/redis.crt"
    redis_key: str | None = "/certs/redis.key"

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_database: str = "dev"
    postgres_user: str = "dev"
    postgres_password: str | None = None
    postgres_use_ssl: bool = False
    postgres_ca_cert: str | None = "/certs/ca.crt"
    postgres_cert: str | None = "/certs/postgres.crt"
    postgres_key: str | None = "/certs/postgres.key"

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = ""
    rabbitmq_use_ssl: bool = False
    rabbitmq_ca_cert: str | None = "/certs/ca.crt"
    rabbitmq_cert: str | None = "/certs/rabbit.crt"
    rabbitmq_key: str | None = "/certs/rabbit.key"

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        case_sensitive=False,
    )



settings = Settings()