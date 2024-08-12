from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str
    API_INITDATA: str

    TAP_RANDOM: list[int] = [30, 50]

    SLEEP_RANDOM: list[int] = [3, 5]
    SLEEP_BETWEEN_MINING: list[int] = [300, 900]

    AUTO_UPGRADE: bool = False
    MAX_LEVEL: int = 20
    BALANCE_TO_SAVE: int = 100000

    AUTO_REFERRALS: bool = False

    APPLY_DAILY_BOOST: bool = False
    USE_PROXY_FROM_FILE: bool = False

settings = Settings()
