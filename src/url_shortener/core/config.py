from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APPLICATION_NAME: str = "WalUrl"

    PORT: int = 7007

    DATABASE_URL: str

    ENVIRONMENT: str = "prod"

    @property
    def IS_DEV_ENV(self) -> bool:
        return self.ENVIRONMENT.lower() in ("dev", "development", "local")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()