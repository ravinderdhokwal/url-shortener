from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APPLICATION_NAME: str = "WalUrl"

    PORT: int = 7007

    DATABASE_URL: str

    DEFAULT_SHORT_CODE_LENGTH: int = 7
    MAX_SHORT_CODE_GENERATION_ATTEMPTS: int = 3

    API_VERSION: int = 1
    @property
    def API_VERSION_PREFIX(self) -> str:
        return f"/api/v{self.API_VERSION}"

    ENVIRONMENT: str = "prod"
    @property
    def IS_DEV_ENV(self) -> bool:
        return self.ENVIRONMENT.lower() in ("dev", "development", "local")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()