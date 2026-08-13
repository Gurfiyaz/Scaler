"""Custom exception classes for DOCX redaction errors."""


class RedactionError(Exception):
    """Base exception for DOCX redaction errors."""
    pass


class DocumentValidationError(RedactionError):
    """Raised when redacted DOCX fails structural integrity check."""
    pass


class ResidualPIIError(RedactionError):
    """Raised when original PII is detected in the redacted output document."""
    pass
