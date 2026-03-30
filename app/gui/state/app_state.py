#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アプリケーション状態管理
"""


class AppState:
    """アプリケーション状態を管理するクラス"""
    
    def __init__(self):
        # UI状態
        self.current_class_index = None
        self.all_assignments = []
        
        # ダウンロード状態
        self.download_in_progress = False
        self.download_thread = None

        # 削除状態
        self.delete_in_progress = False
        self.delete_thread = None

        # ダイアログ参照
        self.device_code_dialog = None

    def reset_download_state(self):
        """ダウンロード状態をリセット"""
        self.download_in_progress = False
        self.download_thread = None

    def reset_delete_state(self):
        """削除状態をリセット"""
        self.delete_in_progress = False
        self.delete_thread = None

    def is_downloading(self):
        """ダウンロード中かどうか"""
        return self.download_in_progress

    def is_deleting(self):
        """削除中かどうか"""
        return self.delete_in_progress

    def is_busy(self):
        """何らかの操作が実行中かどうか"""
        return self.download_in_progress or self.delete_in_progress
    
    def get_selected_class_index(self):
        """選択中のクラスインデックスを取得"""
        return self.current_class_index
    
    def set_selected_class_index(self, index):
        """選択中のクラスインデックスを設定"""
        self.current_class_index = index
