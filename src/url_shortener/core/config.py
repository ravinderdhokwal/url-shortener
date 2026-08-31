from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APPLICATION_NAME: str = "WalUrl"

    PORT: int = 7007

    DATABASE_URL: str

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL_SECONDS: int = 30

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

    PUBLIC_BASE_URL: str = f"localhost:{PORT}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # extra="ignore" -> ignore any environment variables that are not 
    # defined in the Settings class, necessary to pass it here. Without it,
    # Pydantic's default behavior is extra="forbid"  meaning if your .env has 
    # a variable that isn't declared in the class, Pydantic raises a validation error and refuses to start the app

settings = Settings()