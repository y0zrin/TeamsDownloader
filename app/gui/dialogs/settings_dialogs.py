#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定関連ダイアログ（リファクタリング版）
"""

import tkinter as tk
from tkinter import ttk
from gui.dialogs.dialog_utils import create_centered_dialog


class FontSettingsDialog:
    """フォント設定ダイアログ"""
    def __init__(self, parent, current_size):
        self.selected_size = None
        self.dialog = create_centered_dialog(parent, "フォント設定", 380, 350)
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        ttk.Label(
            main_frame,
            text="🔤 フォントサイズ設定",
            font=("", 12, "bold")
        ).pack(pady=(0, 15))
        
        ttk.Label(
            main_frame,
            text="フォントサイズを選択してください:",
            font=("", 10)
        ).pack(pady=(0, 10))
        
        # ラジオボタンフレーム
        radio_frame = ttk.Frame(main_frame)
        radio_frame.pack(fill=tk.BOTH, expand=True)
        
        # ラジオボタン
        self.size_var = tk.StringVar(value=current_size)
        
        size_options = [
            ('smallest', '最小 (8pt)'),
            ('small', '小 (9pt) - デフォルト'),
            ('medium', '中 (10pt)'),
            ('large', '大 (11pt)'),
            ('largest', '最大 (12pt)'),
        ]
        
        for value, label in size_options:
            ttk.Radiobutton(
                radio_frame,
                text=label,
                value=value,
                variable=self.size_var
            ).pack(anchor=tk.W, padx=20, pady=5)
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="適用",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _on_ok(self):
        self.selected_size = self.size_var.get()
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.selected_size = None
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.selected_size
