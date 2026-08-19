from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MySQL
    database_url: str = (
        "mysql+pymysql://root:root@127.0.0.1:3306/singing_exper?charset=utf8mb4"
    )

    # 注意：OSS 凭证不再从环境变量读取，统一从 MySQL 的 `config` 表读取：
    #   oss.endpoint / oss.accessKeyId / oss.accessKeySecret / oss.bucketName

    # CORS
    frontend_origins: str = "http://localhost:5173"

    # 上传限制
    max_pdf_size: int = 104_857_600  # 100MB

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
