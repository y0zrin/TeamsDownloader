#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証関連ダイアログ
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class DeviceCodeDialog:
    """デバイスコード認証用のダイアログ"""
    def __init__(self, parent, user_code, verification_uri):
        self.result = False
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Microsoft認証")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"500x300+{x}+{y}")
        
        # タイトル
        title_label = ttk.Label(
            self.dialog, 
            text="🔐 Microsoft認証が必要です",
            font=("", 14, "bold")
        )
        title_label.pack(pady=20)
        
        # 説明
        info_text = "ブラウザが開きますので、以下のコードを入力してください:"
        info_label = ttk.Label(self.dialog, text=info_text)
        info_label.pack(pady=5)
        
        # コード表示エリア
        code_frame = ttk.Frame(self.dialog)
        code_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.code_entry = ttk.Entry(
            code_frame,
            font=("Courier", 16, "bold"),
            justify=tk.CENTER
        )
        self.code_entry.pack(fill=tk.X, pady=5)
        self.code_entry.insert(0, user_code)
        self.code_entry.configure(state='readonly')
        
        # 自動的にクリップボードにコピー
        try:
            if CLIPBOARD_AVAILABLE:
                import pyperclip
                pyperclip.copy(user_code)
            else:
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(user_code)
        except:
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(user_code)
        
        # コピー済みメッセージ
        copied_label = ttk.Label(
            code_frame,
            text="✓ クリップボードにコピー済み",
            foreground="green"
        )
        copied_label.pack(pady=5)
        
        # URLとボタン
        url_frame = ttk.Frame(self.dialog)
        url_frame.pack(pady=10)
        
        url_label = ttk.Label(url_frame, text=verification_uri, foreground="blue", cursor="hand2")
        url_label.pack()
        url_label.bind("<Button-1>", lambda e: webbrowser.open(verification_uri))
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        open_browser_btn = ttk.Button(
            button_frame,
            text="🌐 ブラウザで開く",
            command=lambda: webbrowser.open(verification_uri)
        )
        open_browser_btn.pack(side=tk.LEFT, padx=5)
        
        # 自動的にブラウザを開く
        try:
            webbrowser.open(verification_uri)
        except:
            pass
        
        # 認証待ちメッセージ
        wait_label = ttk.Label(
            self.dialog,
            text="認証完了を待っています...",
            foreground="gray"
        )
        wait_label.pack(pady=10)
    
    def close(self):
        self.dialog.destroy()
