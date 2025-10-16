#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIダイアログ群
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
import os

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


class ClassCodeSelectionDialog:
    """クラス記号選択ダイアログ"""
    def __init__(self, parent, student_name, class_codes, current_class):
        self.selected_code = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("クラス記号を選択")
        self.dialog.geometry("450x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 150
        self.dialog.geometry(f"450x300+{x}+{y}")
        
        # 説明
        info_frame = ttk.Frame(self.dialog, padding="20")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            info_frame,
            text=f"学生: {student_name}",
            font=("", 11, "bold")
        ).pack(pady=(0, 5))
        
        ttk.Label(
            info_frame,
            text=f"現在のクラス: {current_class}",
            foreground="blue"
        ).pack(pady=(0, 10))
        
        ttk.Label(
            info_frame,
            text="複数のクラス記号があります。\n使用するクラス記号を選択してください:",
            justify=tk.LEFT
        ).pack(pady=(0, 10))
        
        # ラジオボタン
        self.selected_var = tk.StringVar()
        
        # 推奨を最初に設定
        recommended = None
        for code in class_codes:
            if self._is_similar(code, current_class):
                recommended = code
                break
        
        if recommended:
            self.selected_var.set(recommended)
        else:
            self.selected_var.set(class_codes[0])
        
        for code in class_codes:
            # 推奨マークを表示
            if self._is_similar(code, current_class):
                label_text = f"{code} (推奨)"
            else:
                label_text = code
            
            rb = ttk.Radiobutton(
                info_frame,
                text=label_text,
                value=code,
                variable=self.selected_var
            )
            rb.pack(anchor=tk.W, pady=2)
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="スキップ",
            command=self._on_skip,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _is_similar(self, code, class_name):
        """クラス記号がクラス名と類似しているか"""
        class_code = class_name.split('-')[-1] if '-' in class_name else class_name
        common_prefix = os.path.commonprefix([code, class_code])
        return len(common_prefix) >= 4  # 4文字以上一致
    
    def _on_ok(self):
        self.selected_code = self.selected_var.get()
        self.dialog.destroy()
    
    def _on_skip(self):
        self.selected_code = None
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.selected_code
