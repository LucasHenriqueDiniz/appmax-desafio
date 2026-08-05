from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao via variaveis de ambiente (12-factor).

    As URLs externas sao configuraveis para permitir apontar os testes
    para mocks sem tocar em codigo.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://appmax:appmax@localhost:5432/appmax"
    authorizer_url: str = "https://util.devi.tools/api/v2/authorize"
    notifier_url: str = "https://util.devi.tools/api/v1/notify"
    external_timeout_seconds: float = 5.0


settings = Settings()
