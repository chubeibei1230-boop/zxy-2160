from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Locker Reservation API"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8114

    secret_key: str = "locker-reservation-secret-key-2024-please-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    default_max_reservation_hours: int = 4
    auto_checkin_timeout_minutes: int = 15
    overtime_grace_minutes: int = 10

    admin_username: str = "admin"
    admin_password: str = "admin123"
    reception_username: str = "reception"
    reception_password: str = "reception123"
    supervisor_username: str = "supervisor"
    supervisor_password: str = "supervisor123"


settings = Settings()
