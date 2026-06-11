"""
Configuration management for the application.
Reads database configuration from environment variables or config/database.ini.
"""
import os
import logging
from pathlib import Path
from configparser import ConfigParser
from typing import Optional

logger = logging.getLogger(__name__)


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "database.ini"


def _load_ini_config() -> Optional[ConfigParser]:
    """Load configuration from database.ini if it exists."""
    if CONFIG_FILE.exists():
        config = ConfigParser()
        config.read(CONFIG_FILE)
        return config
    return None


def _get_config_value(section: str, key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get a configuration value from environment variable first,
    then fall back to config file.
    """
    # Environment variable takes precedence
    env_key = f"DB_{section.upper()}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value

    # Fall back to config file
    ini_config = _load_ini_config()
    if ini_config and ini_config.has_option(section, key):
        return ini_config.get(section, key)

    return default


def get_db_config() -> dict:
    """
    Get main database configuration.

    Returns:
        dict with keys: host, port, user, password, database, charset
    """
    return {
        "host": _get_config_value("mysql", "host", "localhost"),
        "port": int(_get_config_value("mysql", "port", "3306")),
        "user": _get_config_value("mysql", "user", "root"),
        "password": _get_config_value("mysql", "password", ""),
        "database": _get_config_value("mysql", "database", "channel-analytics"),
        "charset": _get_config_value("mysql", "charset", "utf8mb4"),
    }


def get_ws_db_config() -> dict:
    """
    Get wholesale database configuration.

    Returns:
        dict with keys: host, port, user, password, database, charset
    """
    return {
        "host": _get_config_value("wholesale", "host", "localhost"),
        "port": int(_get_config_value("wholesale", "port", "3306")),
        "user": _get_config_value("wholesale", "user", "root"),
        "password": _get_config_value("wholesale", "password", ""),
        "database": _get_config_value("wholesale", "name", "channel-analytics_ws"),
        "charset": _get_config_value("wholesale", "charset", "utf8mb4"),
    }


def get_session_secret() -> str:
    """
    Get session signing secret.

    Returns:
        Secret key for session/JWT signing
    """
    secret = os.environ.get("SESSION_SECRET")
    if secret:
        return secret

    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
        secret = os.environ.get("SESSION_SECRET")
        if secret:
            return secret
    except ImportError:
        pass

    # Try config file
    ini_config = _load_ini_config()
    if ini_config and ini_config.has_option("security", "session_secret"):
        return ini_config.get("security", "session_secret")

    # No fallback - raise error in production
    raise ValueError(
        "SESSION_SECRET environment variable is not set. "
        "Please set it in .env file or environment."
    )


def get_jwt_secret() -> str:
    """
    Get JWT signing secret.

    Returns:
        Secret key for JWT signing
    """
    secret = os.environ.get("JWT_SECRET")
    if secret:
        return secret

    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
        secret = os.environ.get("JWT_SECRET")
        if secret:
            return secret
    except ImportError:
        pass

    # Fall back to session secret if JWT_SECRET not set
    # (for backwards compatibility during migration)
    logger.warning("JWT_SECRET not configured, falling back to SESSION_SECRET")
    return get_session_secret()
