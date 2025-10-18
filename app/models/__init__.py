"""
ドメインモデル

学生情報、ダウンロード結果などのビジネスオブジェクトを定義
"""

from .student import Student, SharePointStudent, StudentMapping
from .download_result import (
    DownloadedFile,
    StudentDownloadResult,
    DownloadResult,
    UnsubmittedStudent,
    UnsubmittedCheckResult
)

__all__ = [
    'Student',
    'SharePointStudent',
    'StudentMapping',
    'DownloadedFile',
    'StudentDownloadResult',
    'DownloadResult',
    'UnsubmittedStudent',
    'UnsubmittedCheckResult',
]
