from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    GOOGLE_CLOUD_PROJECT: str = "my-project"
    GEMINI_API_KEY: str = ""
    # Stable alias avoids pinning the demo to a retired or capacity-constrained preview.
    GEMINI_MODEL: str = "gemini-flash-latest"
    PARALLEL_API_KEY: str = ""
    GRAFANA_URL: str = ""
    GRAFANA_API_KEY: str = ""
    GRAFANA_SERVICE_ACCOUNT_TOKEN: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

settings = Settings()
