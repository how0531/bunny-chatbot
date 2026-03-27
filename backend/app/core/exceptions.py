"""
Custom exception classes for the stock assistant application.
"""

class StockServiceError(Exception):
    """Base exception for stock service errors."""
    pass

class DatabaseConnectionError(StockServiceError):
    """Raised when database connection fails."""
    pass

class DataNotFoundError(StockServiceError):
    """Raised when requested data is not found."""
    pass

class APIError(StockServiceError):
    """Base exception for API-related errors."""
    pass

class YFinanceAPIError(APIError):
    """Raised when Yahoo Finance API call fails."""
    pass

class CacheError(StockServiceError):
    """Raised when cache operation fails."""
    pass

class ValidationError(StockServiceError):
    """Raised when input validation fails."""
    pass

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass
