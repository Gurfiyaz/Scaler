"""Custom exception classes for DOCX ingestion errors."""


class IngestionError(Exception):
    """Base exception for all document ingestion and parsing errors."""
    pass


class DocumentNotFoundError(IngestionError):
    """Raised when the specified document file path does not exist."""
    pass


class InvalidDocumentError(IngestionError):
    """Raised when the input file is not a valid DOCX container."""
    pass


class CorruptedDocumentError(IngestionError):
    """Raised when the DOCX archive or XML structures are corrupted."""
    pass


class EmptyDocumentError(IngestionError):
    """Raised when the DOCX document contains no readable paragraphs or text."""
    pass
