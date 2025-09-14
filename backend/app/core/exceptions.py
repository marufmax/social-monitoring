"""
Custom exceptions used throughout the application
"""

from typing import Optional, Dict, Any


class SMMMException(Exception):
    """Base exception for Social Media Monitor"""

    def __init__(self, message: str, code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(SMMMException):
    """Authentication related errors"""

    pass


class AuthorizationError(SMMMException):
    """Authorization related errors"""

    pass


class ValidationError(SMMMException):
    """Validation related errors"""

    def __init__(self, message: str, field: str = None, code: str = None):
        self.field = field
        super().__init__(message, code)


class WorkspaceError(SMMMException):
    """Workspace related errors"""

    pass


class ResourceNotFoundError(SMMMException):
    """Resource not found errors"""
    pass