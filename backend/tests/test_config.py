from app.core.config import Settings


def test_settings_cors_origins_parsing():
    settings = Settings(CORS_ORIGINS="http://localhost:3000, http://example.com")
    assert isinstance(settings.CORS_ORIGINS, list)
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://example.com" in settings.CORS_ORIGINS


def test_settings_database_url_sanitization():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://myuser:supersecretpassword@dbhost:5432/mydb"
    )
    sanitized = settings.sanitized_database_url
    assert "supersecretpassword" not in sanitized
    assert "myuser" not in sanitized
    assert "dbhost:5432" in sanitized
    assert "mydb" in sanitized


def test_settings_defaults():
    settings = Settings()
    assert settings.API_V1_STR == "/api/v1"
    assert settings.APP_NAME == "Personal AI Assistant"
