#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カスタム例外クラス
"""


class TeamsDownloaderError(Exception):
    """基底例外"""
    pass


class AuthenticationError(TeamsDownloaderError):
    """認証エラー"""
    pass


class StudentNotFoundError(TeamsDownloaderError):
    """学生が見つからない"""
    def __init__(self, student_name: str, message: str = None):
        self.student_name = student_name
        self.message = message or f"学生が見つかりません: {student_name}"
        super().__init__(self.message)


class DownloadCancelledError(TeamsDownloaderError):
    """ダウンロードがキャンセルされた"""
    pass


class APIError(TeamsDownloaderError):
    """API通信エラー"""
    def __init__(self, status_code: int = None, message: str = None):
        self.status_code = status_code
        self.message = message or f"API通信エラー (status: {status_code})"
        super().__init__(self.message)


class DeleteCancelledError(TeamsDownloaderError):
    """削除がキャンセルされた"""
    pass


class CacheError(TeamsDownloaderError):
    """キャッシュ操作エラー"""
    pass
