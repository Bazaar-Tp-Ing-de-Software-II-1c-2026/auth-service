# config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_MIN: int = 360

    GOOGLE_CLIENT_ID_WEB: str = ""
    GOOGLE_CLIENT_ID_ANDROID: str = ""

    APP_PUBLIC_URL: str = "http://localhost:8000"

    AWS_REGION: str = ""
    S3_BUCKET_NAME: str = ""

    EMAIL_FROM: str = ""
    RESEND_API_KEY: str = ""

    model_config = ConfigDict(extra="ignore")


settings = Settings()