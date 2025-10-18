#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
進捗管理
"""

from typing import Callable, Optional


class ProgressTracker:
    """進捗管理クラス"""
    
    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None):
        self.progress_callback = progress_callback
        self.cancelled = False
    
    def log(self, message: str):
        """ログメッセージを出力"""
        if self.progress_callback:
            self.progress_callback(message)
        else:
            print(message)
    
    def log_header(self, title: str, width: int = 50):
        """ヘッダー付きログを出力"""
        self.log("\n" + "=" * width)
        self.log(title)
        self.log("=" * width)
    
    def log_section(self, title: str):
        """セクションタイトルを出力"""
        self.log(f"\n{title}")
    
    def log_progress(self, current: int, total: int, message: str = ""):
        """進捗状況を出力"""
        if message:
            self.log(f"   📊 進捗: {current}/{total} - {message}")
        else:
            self.log(f"   📊 進捗: {current}/{total}")
    
    def log_success(self, message: str):
        """成功メッセージを出力"""
        self.log(f"✅ {message}")
    
    def log_warning(self, message: str):
        """警告メッセージを出力"""
        self.log(f"⚠️ {message}")
    
    def log_error(self, message: str):
        """エラーメッセージを出力"""
        self.log(f"❌ {message}")
    
    def log_info(self, message: str):
        """情報メッセージを出力"""
        self.log(f"   {message}")
    
    def cancel(self):
        """キャンセルフラグを設定"""
        self.cancelled = True
    
    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.cancelled = False
    
    def check_cancelled(self) -> bool:
        """キャンセルされたかチェック"""
        return self.cancelled
