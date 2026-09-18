from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://carepulse:carepulse@postgres:5432/carepulse"
    JWT_SECRET: str = "change-me-in-development"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"
    ADMIN_DEMO_PASSWORD: str = "CarePulseAdmin!23"
    CLINICIAN_DEMO_PASSWORD: str = "CarePulseClinician!23"
    MODEL_PATH: str = "models/rf_v1.joblib"
    FEATURE_VERSION: str = "fv1"
    CHATBOT_API_KEY: str = ""

    WINDOW_SIZE_READINGS: int = 10
    WINDOW_DURATION_SECONDS: int = 300
    INGEST_INTERVAL_SECONDS: int = 5

    BASELINE_MIN_SAMPLES: int = 20
    BASELINE_MIN_DURATION_SEC: int = 600
    BASELINE_ROLLING_WINDOW: int = 200
    BASELINE_FREEZE_ABOVE_RISK: int = 40

    RISK_STABLE_MAX: int = 24
    RISK_EARLY_CHANGE_MAX: int = 49
    RISK_WARNING_MAX: int = 74

    ESCALATE_CONSECUTIVE: int = 2
    DEESCALATE_CONSECUTIVE: int = 3
    DEESCALATE_MARGIN: int = 8
    MIN_STATE_DWELL_SECONDS: int = 60

    PERSISTENCE_LOOKBACK: int = 6
    PERSISTENCE_ALERT_MIN: int = 3

    ALERT_COOLDOWN_SECONDS: int = 300
    ALERT_DEDUP_WINDOW_SECONDS: int = 900
    ALERT_AUTO_RESOLVE_STABLE_SECONDS: int = 600

    STALE_AFTER_SECONDS: int = 30
    MISSING_AFTER_SECONDS: int = 90
    QUALITY_DEGRADED_BELOW: float = 0.80
    INSUFFICIENT_DATA_BELOW: float = 0.50

    W_ML: float = 0.45
    W_RULE: float = 0.55

    W_DEVIATION: float = 0.30
    W_TREND: float = 0.20
    W_RATE: float = 0.15
    W_PERSISTENCE: float = 0.20
    W_MULTIPARAM: float = 0.15

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    def assert_weight_invariants(self) -> None:
        fusion_total = self.W_ML + self.W_RULE
        rule_total = (
            self.W_DEVIATION
            + self.W_TREND
            + self.W_RATE
            + self.W_PERSISTENCE
            + self.W_MULTIPARAM
        )
        assert abs(fusion_total - 1.0) < 1e-9, f"W_ML + W_RULE must equal 1, got {fusion_total}"
        assert abs(rule_total - 1.0) < 1e-9, f"rule component weights must equal 1, got {rule_total}"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.assert_weight_invariants()
    return settings
