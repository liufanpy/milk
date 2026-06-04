from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///milk.db"
    app_name: str = "奶记"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
