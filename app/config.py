from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from pathlib import Path

# Ruta absoluta al archivo .env desde /app/config.py hacia la raíz
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    APP_NAME: str = "BioGenetic API"
    DEBUG: bool = False

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET_NAME: str

    # ePayco Configuration
    EPAYCO_PUBLIC_KEY: str = Field(..., description="ePayco Public Key")
    EPAYCO_PRIVATE_KEY: str = Field(..., description="ePayco Private Key")
    EPAYCO_TEST_MODE: bool = Field(True, description="ePayco Test Mode")
    EPAYCO_MERCHANT_ID: str = Field(..., description="ePayco Merchant ID")

    # Email Configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@biogenetic.com"
    FROM_NAME: str = "BioGenetic"


    # URLs
    BASE_URL: str = Field(..., description="Base URL of the application")
    PAYMENT_RESPONSE_URL: str = Field(..., description="Payment response callback URL")
    PAYMENT_CONFIRMATION_URL: str = Field(..., description="Payment confirmation callback URL")

    @field_validator("*", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        return value.strip() if isinstance(value, str) else value

    class Config:
        env_file = str(ENV_PATH)
        env_file_encoding = "utf-8"

settings = Settings()


