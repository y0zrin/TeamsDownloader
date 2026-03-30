#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題削除サービス
"""

from typing import Optional, Callable
from models.delete_result import DeleteResult
from services.delete_core.deleter import AssignmentDeleter


class DeleteService:
    """課題削除を管理するサービス"""

    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.deleter = AssignmentDeleter(api_client, cache_manager)

    def delete_assignment(
        self,
        class_config: dict,
        assignment_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> DeleteResult:
        """課題をSharePointから削除

        Args:
            class_config: クラス設定
            assignment_name: 課題名
            progress_callback: 進捗コールバック

        Returns:
            DeleteResult: 削除結果
        """
        return self.deleter.delete_assignment(
            class_config,
            assignment_name,
            progress_callback,
        )

    def cancel(self):
        """削除をキャンセル"""
        self.deleter.cancel()

    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.deleter.reset_cancel()

    @property
    def cancelled(self) -> bool:
        """キャンセル状態を取得"""
        return self.deleter.progress.check_cancelled()
