"""
ユーティリティ

ファイル操作、暗号化、例外などの汎用機能を提供
"""

from .file_utils import (
    sanitize_filename,
    detect_excel_format,
    check_drm_protection,
    clean_student_name,
)
from .crypto import (
    ENCRYPTION_AVAILABLE,
    encrypt_data,
    decrypt_data,
    get_or_create_encryption_key,
)
from .exceptions import (
    TeamsDownloaderError,
    AuthenticationError,
    StudentNotFoundError,
    DownloadCancelledError,
    APIError,
    CacheError,
)

__all__ = [
    'sanitize_filename',
    'detect_excel_format',
    'check_drm_protection',
    'clean_student_name',
    'ENCRYPTION_AVAILABLE',
    'encrypt_data',
    'decrypt_data',
    'get_or_create_encryption_key',
    'TeamsDownloaderError',
    'AuthenticationError',
    'StudentNotFoundError',
    'DownloadCancelledError',
    'APIError',
    'CacheError',
]
