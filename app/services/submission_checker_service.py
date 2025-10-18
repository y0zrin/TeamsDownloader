#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未提出者確認サービス（公開API）

GUIから呼ばれる未提出者確認の公開インターフェース
"""

from typing import Optional, Callable, List, Tuple
from services.download_core.submission_checker import SubmissionChecker


class SubmissionCheckerService:
    """未提出者確認サービス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.checker = SubmissionChecker(api_client, cache_manager)
    
    def get_unsubmitted_students(
        self,
        class_config: dict,
        assignment_name: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[List[dict], Optional[str]]:
        """未提出者を取得
        
        Args:
            class_config: クラス設定
            assignment_name: 課題名
            progress_callback: 進捗コールバック
        
        Returns:
            (未提出者リスト, エラーメッセージ)
        """
        return self.checker.check_unsubmitted(
            class_config,
            assignment_name,
            progress_callback
        )
