# config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_MIN: int = 360

    GOOGLE_CLIENT_ID_WEB: str = ""
    GOOGLE_CLIENT_ID_ANDROID: str = ""

    AWS_REGION: str = ""
    S3_BUCKET_NAME: str = ""

    EMAIL_FROM: str = ""
    RESEND_API_KEY: str = ""

    model_config = ConfigDict(extra="ignore")


settings = Settings()