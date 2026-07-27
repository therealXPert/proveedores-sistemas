"""
Configuracion de la aplicacion, leida desde variables de entorno.
En Cloud Run estas variables se inyectan desde Secret Manager / env vars
definidas en el modulo de Terraform cloud_run_api.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Control de Gasto Sistemas - API"
    environment: str = "dev"

    db_instance_connection_name: str = ""  # ej: proyecto:region:instancia
    db_name: str = "control_gasto"
    db_user: str = "app_user"
    db_password: str = ""

    app_secret_key: str = "cambiar-en-produccion"

    gcs_bucket: str = ""

    @property
    def database_url(self) -> str:
        if self.environment == "local":
            return f"postgresql+psycopg://{self.db_user}:{self.db_password}@localhost:5432/{self.db_name}"
        socket_path = f"/cloudsql/{self.db_instance_connection_name}"
        return f"postgresql+psycopg://{self.db_user}:{self.db_password}@/{self.db_name}?host={socket_path}"

    class Config:
        env_file = ".env"


settings = Settings()
