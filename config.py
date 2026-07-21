from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    rate_limit: int = 100

    debug: bool = False

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_database: str = "development"
    postgres_user: str = "dev"
    postgres_password: str | None = None

    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = ""

    use_argon: bool = False

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
