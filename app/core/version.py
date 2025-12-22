#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
バージョン管理とアップデート確認
"""

import threading
import webbrowser
from tkinter import messagebox

# 現在のバージョン
VERSION = "1.0.1"

# バージョン情報のURL（GitHub Gist）
VERSION_URL = "https://gist.githubusercontent.com/y0zrin/b8fe7992f0a823c3e8c4856dc96a45a6/raw/version.json"


def compare_versions(current: str, latest: str) -> int:
    """バージョンを比較
    
    Returns:
        -1: current < latest（アップデートあり）
         0: current == latest
         1: current > latest
    """
    def parse_version(v):
        return [int(x) for x in v.split('.')]
    
    current_parts = parse_version(current)
    latest_parts = parse_version(latest)
    
    # 長さを揃える
    max_len = max(len(current_parts), len(latest_parts))
    current_parts.extend([0] * (max_len - len(current_parts)))
    latest_parts.extend([0] * (max_len - len(latest_parts)))
    
    for c, l in zip(current_parts, latest_parts):
        if c < l:
            return -1
        elif c > l:
            return 1
    return 0


class UpdateChecker:
    """アップデート確認クラス"""
    
    def __init__(self, root, log_callback=None):
        self.root = root
        self.log = log_callback or print
    
    def check_for_updates_async(self):
        """非同期でアップデートを確認"""
        thread = threading.Thread(target=self._check_updates, daemon=True)
        thread.start()
    
    def _check_updates(self):
        """アップデート確認（バックグラウンド）"""
        try:
            import requests
            import time
            
            # キャッシュ回避のためタイムスタンプを追加
            url = f"{VERSION_URL}?t={int(time.time())}"
            
            # キャッシュ無効化ヘッダーを追加
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                return
            
            data = response.json()
            latest_version = data.get('version', VERSION)
            release_notes = data.get('release_notes', '')
            download_url = data.get('download_url', '')
            
            # バージョン比較
            if compare_versions(VERSION, latest_version) < 0:
                # 新しいバージョンがある
                self.root.after(0, lambda: self._show_update_dialog(
                    latest_version, release_notes, download_url
                ))
            else:
                self.log(f"✅ 最新バージョンです (v{VERSION})")
        
        except Exception as e:
            # エラーは静かに無視（ネットワーク不通など）
            pass
    
    def _show_update_dialog(self, latest_version, release_notes, download_url):
        """アップデート通知ダイアログを表示"""
        message = f"新しいバージョンがあります！\n\n"
        message += f"現在: v{VERSION}\n"
        message += f"最新: v{latest_version}\n"
        
        if release_notes:
            message += f"\n更新内容:\n{release_notes}\n"
        
        message += "\nダウンロードページを開きますか？"
        
        if messagebox.askyesno("アップデート通知", message):
            if download_url:
                webbrowser.open(download_url)
