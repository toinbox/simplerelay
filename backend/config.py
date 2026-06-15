from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://simplerelay:simplerelay@db:5432/simplerelay"
    secret_key: str = "change-me-in-production"
    port: int = 2525
    hostname: str = "relay.example.com"
    public_ip: str = ""
    web_port: int = 8080
    default_language: str = "en"
    supported_languages: list[str] = ["en", "cs", "de", "ru", "es"]
    data_dir: str = "/data"

    # Default admin account
    admin_email: str = "admin@simplerelay.local"
    admin_password: str = "changeme123"

    # System SMTP for verification/reset emails
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@simplerelay.local"
    smtp_tls: bool = True
    base_url: str = "http://localhost:8080"  # for verification links

    class Config:
        env_prefix = "RELAY_"
        env_file = ".env"


settings = Settings()
