from dynaconf import Dynaconf

__all__ = [
    "SETTINGS",
    "LOGGING_SETTINGS",
    "DB_SETTINGS",
    "HTTP_SETTINGS",
    "PRICES_SETTINGS",
]

SETTINGS = Dynaconf(
    merge_enabled=True,
    envvar_prefix="FARMRPG_MARKETPRICES",
    settings_files=[
        "config/settings.toml",
        "config/.secrets.toml",
        "settings.toml",
        ".secrets.toml",
    ],
)

LOGGING_SETTINGS = SETTINGS.get("logging", {})
DB_SETTINGS = SETTINGS.get("database", {})
HTTP_SETTINGS = SETTINGS.get("http", {})
PRICES_SETTINGS = SETTINGS.get("prices", {})
