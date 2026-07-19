from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "学生心理关怀随访与报表系统"
    environment: str = "development"
    secret_key: str = "development-secret-key-change-before-production"
    access_token_expire_minutes: int = 480
    database_url: str = "sqlite:///./student_care.db"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    auto_create_tables: bool = True
    timezone: str = "Asia/Shanghai"

    initial_admin_username: str = "admin"
    initial_admin_password: str = "ChangeMe123!"
    initial_admin_name: str = "系统管理员"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() != "production":
            return self
        if (
            len(self.secret_key) < 32
            or "change" in self.secret_key.lower()
            or "replace" in self.secret_key.lower()
        ):
            raise ValueError("生产环境必须配置至少 32 位且非默认的 SECRET_KEY")
        if self.initial_admin_password in {"ChangeMe123!", "Admin123!"}:
            raise ValueError("生产环境必须修改 INITIAL_ADMIN_PASSWORD")
        if "change-this" in self.database_url.lower():
            raise ValueError("生产环境必须修改数据库密码")
        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
