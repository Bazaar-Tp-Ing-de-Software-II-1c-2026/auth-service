# config.py
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str

    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_MIN: int = 360

    PRODUCT_SERVICE_URL: str = ""
    GOOGLE_CLIENT_ID_WEB: str = ""
    GOOGLE_CLIENT_ID_ANDROID: str = ""

    AWS_REGION: str = ""
    S3_BUCKET_NAME: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_ACCESS_KEY_ID: str = ""

    EMAIL_FROM: str = ""
    RESEND_API_KEY: str = ""
    SKIP_EMAIL_VERIFICATION: bool = False
    PRODUCT_SERVICE_URL: str = ""
    model_config = ConfigDict(extra="ignore", env_file=".env", env_file_encoding="utf-8")


settings = Settings()
