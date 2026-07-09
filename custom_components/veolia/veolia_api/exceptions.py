"""Custom exception classes for Veolia API errors"""


class VeoliaAPIError(Exception):
    """Base exception class for Veolia API errors"""


class VeoliaAPIInvalidCredentialsError(VeoliaAPIError):
    """Exception for missing or rejected credentials"""


class VeoliaAPITokenError(VeoliaAPIError):
    """Exception for access-token retrieval or validation failures"""


class VeoliaAPIResponseError(VeoliaAPIError):
    """Exception for unexpected API response payloads"""


class VeoliaAPIGetDataError(VeoliaAPIError):
    """Exception for data-fetching failures"""


class VeoliaAPISetDataError(VeoliaAPIError):
    """Exception for data-writing failures"""


class VeoliaAPIUnknownError(VeoliaAPIError):
    """Exception for unknown Veolia API errors"""


class VeoliaAPIRateLimitError(VeoliaAPIError):
    """Exception for HTTP 429 Too Many Requests."""
