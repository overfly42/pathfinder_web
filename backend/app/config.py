from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable via environment variables or a `.env` file.

    Defaults match `docker-compose.yml`'s `db` service, so local dev works with
    zero configuration once that container is up.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://pathfinder:pathfinder@localhost:5432/pathfinder"


settings = Settings()
