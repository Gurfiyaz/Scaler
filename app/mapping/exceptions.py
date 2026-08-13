"""Custom exception classes for entity mapping errors."""


class MappingError(Exception):
    """Base exception for entity mapping failures."""
    pass


class CollisionError(MappingError):
    """Raised when a generated replacement collides with an existing mapping."""
    pass


class InvalidReplacementError(MappingError):
    """Raised when a generated synthetic replacement fails validation."""
    pass
