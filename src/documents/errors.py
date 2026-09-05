"""
Structured document-intelligence errors (MRPL Phase 2).

Every failure mode carries a stable machine-readable ``code`` and a safe,
actionable ``message``. The API layer maps these to HTTP responses without ever
leaking document contents. NEVER put extracted/confidential text in a message.
"""


class DocumentError(Exception):
    """Base class for all document-intelligence failures.

    ``code`` is a stable slug for programmatic handling; ``message`` is a safe,
    user-facing explanation (no document contents).
    """

    code = "document_error"
    http_status = 400

    def __init__(self, message: str, *, code: str = None, http_status: int = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status

    def to_dict(self) -> dict:
        return {"error": self.message, "code": self.code}


class UnsupportedFileTypeError(DocumentError):
    code = "unsupported_file_type"
    http_status = 415


class FileTooLargeError(DocumentError):
    code = "file_too_large"
    http_status = 413


class CorruptedDocumentError(DocumentError):
    code = "corrupted_document"
    http_status = 422


class EmptyDocumentError(DocumentError):
    code = "empty_document"
    http_status = 422


class InvalidImageError(DocumentError):
    code = "invalid_image"
    http_status = 422


class OCRUnavailableError(DocumentError):
    """Raised when a document REQUIRES OCR but no OCR engine is usable.

    This is surfaced (never swallowed into empty text) so the operator gets a
    clear, actionable instruction to install the local OCR toolchain.
    """

    code = "ocr_unavailable"
    http_status = 503


class ExtractionError(DocumentError):
    code = "extraction_failed"
    http_status = 500
