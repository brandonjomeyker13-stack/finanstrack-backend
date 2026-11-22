from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Una sola lectura del entorno. Local: archivo `.env`. Render: Environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Finanstrack"
    API_V1_PREFIX: str = "/api/v1"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Supabase Postgres. Ver .env.example: session pooler, puerto 5432.
    DATABASE_URL: str

    # No las usa el motor de SQL. Quedan en el entorno para tenerlas a mano
    # (panel de Supabase → Settings → API) y para un cliente futuro.
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    CORS_ORIGINS: str = "http://localhost:5173"
    CORS_ORIGIN_REGEX: str | None = None
    FRONTEND_URL: str = "http://localhost:5173"

    ZONA_HORARIA: str = "America/Bogota"

    # Google Cloud → Credenciales → ID de cliente de OAuth (aplicación web).
    # El mismo valor va en el front como VITE_GOOGLE_CLIENT_ID.
    # Vacío: la API arranca igual y el botón avisa que falta configurarlo.
    GOOGLE_CLIENT_ID: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origen.strip() for origen in self.CORS_ORIGINS.split(",") if origen.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def sqlalchemy_url(self) -> str:
        """Acepta el URI que copia Supabase (`postgres://` o `postgresql://`)."""
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://") :]
        if url.startswith("postgresql+") and "sslmode=" not in url and "localhost" not in url:
            separador = "&" if "?" in url else "?"
            url = f"{url}{separador}sslmode=require"
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
