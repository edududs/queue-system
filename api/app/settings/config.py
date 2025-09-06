from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Core
    PROJECT_NAME: str = "Queue System API"
    DEBUG: bool = True

    # Timezone
    DEFAULT_TIMEZONE: str = "UTC"
    USER_TIMEZONE: str = "America/Sao_Paulo"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # JWT
    SECRET_KEY: str = "xyz"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "queue_system"

    @property
    def DATABASE_URL(self) -> str:
        # pymysql driver (sync)
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    # Redis (futuro)
    REDIS_URL: str = "redis://localhost:6379"

    # RabbitMQ (topologia)
    RABBITMQ_URL: str = "amqp://guest:guest@localhost/"
    RABBITMQ_EXCHANGE: str = "tasks"  # direct exchange
    RABBITMQ_MAIN_QUEUE: str = "tasks.main"
    RABBITMQ_RETRY_QUEUE: str = "tasks.retry"
    RABBITMQ_DLQ: str = "tasks.dlq"
    RABBITMQ_RETRY_DELAY_MS: int = 30000
    RABBITMQ_MAX_RETRIES: int = 5
    RABBITMQ_PREFETCH_COUNT: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
