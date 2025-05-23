import os
import typing

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    VERSION: str = os.getenv("VERSION", "0.1.0")
    APP_TITLE: str = os.getenv("APP_TITLE", "Vue FastAPI Admin")
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Vue FastAPI Admin")
    APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION", "Description")

    CORS_ORIGINS: typing.List = eval(os.getenv("CORS_ORIGINS", '["*"]'))
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    CORS_ALLOW_METHODS: typing.List = eval(os.getenv("CORS_ALLOW_METHODS", '["*"]'))
    CORS_ALLOW_HEADERS: typing.List = eval(os.getenv("CORS_ALLOW_HEADERS", '["*"]'))

    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

    TORTOISE_ORM: dict = {
        "connections": {
            os.getenv("DB_ENGINE", "postgres"): {
                "engine": f"tortoise.backends.{os.getenv('DB_ENGINE', 'asyncpg')}",
                "credentials": {
                    "host": os.getenv("DB_HOST", "localhost"),
                    "port": int(os.getenv("DB_PORT", "5432")),
                    "user": os.getenv("DB_USER", "admin"),
                    "password": os.getenv("DB_PASSWORD", "123456"),
                    "database": os.getenv("DB_NAME", "school_db_test"),
                },
            },
        },
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": os.getenv("DB_ENGINE", "postgres"),
            },
        },
        "use_tz": os.getenv("USE_TZ", "false").lower() == "true",
        "timezone": os.getenv("TIMEZONE", "Asia/Shanghai"),
    }
    
    DATETIME_FORMAT: str = os.getenv("DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S")


settings = Settings()
