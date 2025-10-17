"""
コアモジュール

認証、API通信、キャッシュ管理、学生情報管理などの基本機能を提供
"""

from .auth import AuthManager
from .api_client import GraphAPIClient
from .cache import AssignmentCache
from .students import load_students_info

__all__ = [
    'AuthManager',
    'GraphAPIClient',
    'AssignmentCache',
    'load_students_info',
]
