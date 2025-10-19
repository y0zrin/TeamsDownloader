#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
進捗・完了関連ダイアログ
"""

import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox


class ProgressDialog:
    """プログレスバー表示ダイアログ（モーダル）"""
    def __init__(self, parent, title="処理中", message="処理を実行しています..."):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # 閉じるボタンを無効化
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 100
        self.dialog.geometry(f"500x200+{x}+{y}")
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトルラベル
        self.title_label = ttk.Label(
            main_frame,
            text=title,
            font=("", 12, "bold")
        )
        self.title_label.pack(pady=(0, 15))
        
        # メッセージラベル
        self.message_label = ttk.Label(
            main_frame,
            text=message,
            font=("", 10)
        )
        self.message_label.pack(pady=(0, 10))
        
        # プログレスバー（不確定モード）
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=(0, 10))
        self.progress.start(10)  # アニメーション開始
        
        # 詳細メッセージラベル
        self.detail_label = ttk.Label(
            main_frame,
            text="",
            font=("", 9),
            foreground="gray"
        )
        self.detail_label.pack(pady=(10, 0))
        
        # ダイアログを更新
        self.dialog.update()
    
    def update_message(self, message):
        """メッセージを更新"""
        self.message_label.config(text=message)
        self.dialog.update()
    
    def update_detail(self, detail):
        """詳細メッセージを更新"""
        self.detail_label.config(text=detail)
        self.dialog.update()
    
    def close(self):
        """ダイアログを閉じる"""
        try:
            self.progress.stop()
            self.dialog.destroy()
        except:
            pass


class DownloadCompleteDialog:
    """ダウンロード完了ダイアログ（フォルダを開くボタン付き）"""
    def __init__(self, parent, student_count, file_count, folder_path):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("ダウンロード完了")
        self.dialog.geometry("450x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 125
        self.dialog.geometry(f"450x250+{x}+{y}")
        
        self.folder_path = folder_path
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # アイコンとタイトル
        ttk.Label(
            main_frame,
            text="✅ ダウンロード完了",
            font=("", 14, "bold"),
            foreground="green"
        ).pack(pady=(0, 20))
        
        # 統計情報
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(pady=(0, 20))
        
        ttk.Label(
            info_frame,
            text=f"学生数: {student_count}人",
            font=("", 11)
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Label(
            info_frame,
            text=f"ファイル数: {file_count}個",
            font=("", 11)
        ).pack(anchor=tk.W, pady=2)
        
        # 保存先パス（短縮表示）
        path_label = ttk.Label(
            main_frame,
            text=f"保存先: {self._shorten_path(folder_path)}",
            font=("", 9),
            foreground="gray"
        )
        path_label.pack(pady=(0, 20))
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="📁 フォルダを開く",
            command=self._open_folder,
            width=18
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="閉じる",
            command=self.dialog.destroy,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _shorten_path(self, path):
        """パスを短縮表示"""
        if len(path) <= 50:
            return path
        # 先頭と末尾を残して中間を省略
        return path[:20] + "..." + path[-27:]
    
    def _open_folder(self):
        """フォルダを開く"""
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(self.folder_path)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", self.folder_path])
            else:  # Linux
                subprocess.Popen(["xdg-open", self.folder_path])
        except Exception as e:
            messagebox.showerror("エラー", f"フォルダを開けませんでした:\n{e}")
    
    def show(self):
        """ダイアログを表示"""
        self.dialog.wait_window()
