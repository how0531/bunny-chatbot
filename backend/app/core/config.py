"""
Configuration management module.
Loads environment variables and provides centralized configuration.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
# Root is backend/app/core -> ../../../..
env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Application configuration class."""
    
    # MongoDB Configuration
    MONGODB_URI: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_TIMEOUT: int = int(os.getenv('MONGODB_TIMEOUT', '5000'))
    MONGODB_MAX_POOL_SIZE: int = int(os.getenv('MONGODB_MAX_POOL_SIZE', '50'))
    MONGODB_MIN_POOL_SIZE: int = int(os.getenv('MONGODB_MIN_POOL_SIZE', '10'))
    
    # Flask Configuration
    FLASK_ENV: str = os.getenv('FLASK_ENV', 'production')
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_PORT: int = int(os.getenv('FLASK_PORT', '5000'))
    
    # Cache Configuration (TTL in seconds)
    CACHE_NAME_TTL: int = int(os.getenv('CACHE_NAME_TTL', '86400'))
    CACHE_ANALYSIS_TTL: int = int(os.getenv('CACHE_ANALYSIS_TTL', '600'))
    CACHE_CONCEPT_TTL: int = int(os.getenv('CACHE_CONCEPT_TTL', '1800'))
    CACHE_YFINANCE_TTL: int = int(os.getenv('CACHE_YFINANCE_TTL', '3600'))
    
    # Application Settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: Optional[str] = os.getenv('LOG_FILE', None)  # None = stdout
    MAX_BATCH_STOCKS: int = int(os.getenv('MAX_BATCH_STOCKS', '5'))
    MAX_HISTORICAL_RECORDS: int = int(os.getenv('MAX_HISTORICAL_RECORDS', '5'))
    
    # Metabase Configuration
    METABASE_URL: str = os.getenv('METABASE_URL', 'http://localhost:3000')
    METABASE_USERNAME: str = os.getenv('METABASE_USERNAME', '')
    METABASE_PASSWORD: str = os.getenv('METABASE_PASSWORD', '')
    
    # External APIs
    TAVILY_API_KEY: str = os.getenv('TAVILY_API_KEY', '')

    @classmethod
    def validate(cls) -> None:
        """
        Validate required configuration.
        Raises ValueError if critical configuration is missing.
        """
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required. Please set it in .env file.")
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode."""
        return cls.FLASK_ENV == 'development'
    
    @classmethod
    def get_log_level(cls) -> int:
        """Get logging level as integer."""
        import logging
        return getattr(logging, cls.LOG_LEVEL.upper(), logging.INFO)

# Validate configuration on module import (soft check)
try:
    Config.validate()
except ValueError as e:
    import logging as _log
    _log.warning(f"Config validation warning: {e} - App will start with defaults.")
