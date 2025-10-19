#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クラス管理パネル
"""

import tkinter as tk
from tkinter import ttk
from gui.widgets.tooltip import ToolTip


class ClassPanel:
    """クラス管理パネル"""
    
    def __init__(self, parent, font_size, handlers):
        """
        Args:
            parent: 親ウィジェット
            font_size: フォントサイズ
            handlers: ハンドラ辞書
                - add_class: クラス追加ハンドラ
                - edit_class: クラス編集ハンドラ
                - delete_class: クラス削除ハンドラ
                - debug_folder: フォルダ構造確認ハンドラ
                - show_settings: 設定メニューハンドラ
                - on_class_select: クラス選択ハンドラ
        """
        self.handlers = handlers
        self.font_size = font_size
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        
        # ボタンフレーム
        self._create_buttons(parent)
        
        # クラスリスト
        self._create_list(parent)
    
    def _create_buttons(self, parent):
        """ボタンを作成"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 1行目のボタン
        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(fill=tk.X, pady=(0, 2))
        
        add_btn = ttk.Button(
            button_row1,
            text="➕ 追加",
            command=self.handlers['add_class']
        )
        add_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(add_btn, "新しいクラスを追加")
        
        edit_btn = ttk.Button(
            button_row1,
            text="✏️ 編集",
            command=self.handlers['edit_class']
        )
        edit_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(edit_btn, "選択したクラス名を編集")
        
        delete_btn = ttk.Button(
            button_row1,
            text="🗑️ 削除",
            command=self.handlers['delete_class']
        )
        delete_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(delete_btn, "選択したクラスを削除")
        
        # 2行目のボタン
        button_row2 = ttk.Frame(button_frame)
        button_row2.pack(fill=tk.X)
        
        structure_btn = ttk.Button(
            button_row2,
            text="📁 構造",
            command=self.handlers['debug_folder']
        )
        structure_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(structure_btn, "SharePointのフォルダ構造を確認")
        
        settings_btn = ttk.Button(
            button_row2,
            text="⚙️ 設定",
            command=self.handlers['show_settings']
        )
        settings_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(settings_btn, "設定メニューを開く")
        
        # 設定メニュー用の参照を保持
        self.settings_button = settings_btn
    
    def _create_list(self, parent):
        """クラスリストを作成"""
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.class_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", self.font_size),
            selectmode=tk.SINGLE
        )
        self.class_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.class_listbox.yview)
        
        # 選択イベント
        self.class_listbox.bind('<<ListboxSelect>>', self.handlers['on_class_select'])
    
    def get_listbox(self):
        """リストボックスを取得"""
        return self.class_listbox
    
    def get_settings_button(self):
        """設定ボタンを取得"""
        return self.settings_button
    
    def update_font(self, font_size):
        """フォントサイズを更新"""
        self.font_size = font_size
        self.class_listbox.configure(font=("", font_size))
