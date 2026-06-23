"""
Custom exceptions for the RFID card system.
"""


class CardServiceError(Exception):
    """Base exception for card service operations."""
    pass


class CardNotFoundError(CardServiceError):
    """Raised when a card with the specified UID is not found."""
    pass


class CardNotActiveError(CardServiceError):
    """Raised when trying to perform operations on an inactive card."""
    pass


class InsufficientBalanceError(CardServiceError):
    """Raised when there's insufficient balance for an operation."""
    pass


class InvalidAmountError(CardServiceError):
    """Raised when an invalid amount is provided."""
    pass


class CardAlreadyExistsError(CardServiceError):
    """Raised when trying to create a card that already exists."""
    pass


class InvalidStatusError(CardServiceError):
    """Raised when an invalid card status is provided."""
    pass

