#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題ダウンロードサービス（リファクタリング版）

ダウンロード機能のみを提供
未提出者確認はSubmissionCheckerに分離
"""

from typing import Optional, Callable, List, Tuple
from services.download_core.coordinator import DownloadCoordinator


class DownloadService:
    """課題ダウンロードを管理するサービス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.coordinator = DownloadCoordinator(api_client, cache_manager)
    
    def download_assignment(
        self,
        class_config: dict,
        assignment_name: str,
        output_base_dir: str,
        progress_callback: Optional[Callable[[str], None]] = None,
        class_code_dialog_callback: Optional[Callable] = None,
        selected_students: Optional[List[str]] = None,
        name_mapping_dialog_callback: Optional[Callable] = None
    ) -> Tuple[int, int]:
        """課題をダウンロード
        
        Args:
            class_config: クラス設定
            assignment_name: 課題名
            output_base_dir: 出力ベースディレクトリ
            progress_callback: 進捗コールバック
            class_code_dialog_callback: クラス記号選択ダイアログコールバック
            selected_students: ダウンロード対象の学生名リスト（オプション）
            name_mapping_dialog_callback: 名前マッピングダイアログコールバック
        
        Returns:
            (成功数, 学生数)
        """
        result = self.coordinator.download_assignment(
            class_config,
            assignment_name,
            output_base_dir,
            progress_callback,
            class_code_dialog_callback,
            selected_students,
            name_mapping_dialog_callback
        )
        
        return result.file_count, result.student_count
    
    def cancel(self):
        """ダウンロードをキャンセル"""
        self.coordinator.cancel()
    
    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.coordinator.reset_cancel()
    
    @property
    def cancelled(self) -> bool:
        """キャンセル状態を取得"""
        return self.coordinator.progress.check_cancelled()
