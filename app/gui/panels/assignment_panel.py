#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題リストパネル
"""

import tkinter as tk
from tkinter import ttk


class AssignmentPanel:
    """課題リストパネル"""
    
    def __init__(self, parent, font_size, handlers):
        """
        Args:
            parent: 親ウィジェット
            font_size: フォントサイズ
            handlers: ハンドラ辞書
                - refresh: 課題更新ハンドラ
                - check_unsubmitted: 未提出者確認ハンドラ
                - select_students: 学生選択ハンドラ
                - download: ダウンロードハンドラ
                - cancel_download: キャンセルハンドラ
                - delete: 課題削除ハンドラ
                - cancel_delete: 削除キャンセルハンドラ
                - filter: フィルタハンドラ（オプション）
        """
        self.handlers = handlers
        self.font_size = font_size
        self.search_var = None
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)  # リストエリアの行
        
        # 上部: ステータスラベル
        self.status_label = ttk.Label(
            parent,
            text="クラスを選択してください",
            font=("", font_size),
            foreground="gray"
        )
        self.status_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # 課題リスト（検索含む）
        self._create_list(parent)
        
        # 下部ボタンフレーム
        self._create_buttons(parent)
    
    def _create_list(self, parent):
        """課題リストを作成"""
        # 検索フレーム
        search_frame = ttk.Frame(parent)
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="🔍").grid(row=0, column=0, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # 検索フィルタを設定（ハンドラ経由）
        if 'filter' in self.handlers:
            self.search_var.trace('w', lambda *args: self.handlers['filter']())
        
        # 課題リスト
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.assignment_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", self.font_size)
        )
        self.assignment_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.assignment_listbox.yview)
        
        # ダブルクリックでダウンロード
        self.assignment_listbox.bind('<Double-1>', lambda e: self.handlers['download']())
        
        # 更新ボタン
        update_frame = ttk.Frame(parent)
        update_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 5))
        
        ttk.Button(
            update_frame,
            text="🔄 課題を手動更新",
            command=self.handlers['refresh']
        ).pack(fill=tk.X)
    
    def _create_buttons(self, parent):
        """下部ボタンを作成"""
        self.bottom_button_frame = ttk.Frame(parent)
        self.bottom_button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self.bottom_button_frame.columnconfigure(0, weight=1)
        self.bottom_button_frame.columnconfigure(1, weight=1)
        self.bottom_button_frame.columnconfigure(2, weight=1)
        
        # 通常時の3つのボタン
        self.unsubmitted_btn = ttk.Button(
            self.bottom_button_frame,
            text="📊 未提出者一覧を出力",
            command=self.handlers['check_unsubmitted']
        )
        self.unsubmitted_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        
        self.select_students_btn = ttk.Button(
            self.bottom_button_frame,
            text="👥 学生を指定してDL",
            command=self.handlers['select_students']
        )
        self.select_students_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        
        self.download_button = ttk.Button(
            self.bottom_button_frame,
            text="📥 一括ダウンロード",
            command=self.handlers['download']
        )
        self.download_button.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(2, 0))

        # 2行目: 削除ボタン
        self.delete_btn = ttk.Button(
            self.bottom_button_frame,
            text="🗑️ サーバーから削除",
            command=self.handlers.get('delete', lambda: None)
        )
        self.delete_btn.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))

        # キャンセルボタン（操作中のみ表示）
        self.cancel_button = ttk.Button(
            self.bottom_button_frame,
            text="❌ キャンセル",
            command=self.handlers['cancel_download']
        )
        self.cancel_button.grid(row=0, column=0, columnspan=3, rowspan=2, sticky=(tk.W, tk.E))
        self.cancel_button.grid_remove()
    
    def show_download_buttons(self):
        """通常のボタンを表示"""
        self.cancel_button.grid_remove()
        self.unsubmitted_btn.grid()
        self.select_students_btn.grid()
        self.download_button.grid()
        self.delete_btn.grid()

    def show_cancel_button(self, cancel_command=None):
        """キャンセルボタンのみを表示

        Args:
            cancel_command: キャンセル時に呼ぶコールバック（省略時はcancel_download）
        """
        self.unsubmitted_btn.grid_remove()
        self.select_students_btn.grid_remove()
        self.download_button.grid_remove()
        self.delete_btn.grid_remove()
        if cancel_command:
            self.cancel_button.config(command=cancel_command)
        else:
            self.cancel_button.config(command=self.handlers['cancel_download'])
        self.cancel_button.grid()
    
    def get_listbox(self):
        """リストボックスを取得"""
        return self.assignment_listbox
    
    def get_status_label(self):
        """ステータスラベルを取得"""
        return self.status_label
    
    def get_search_var(self):
        """検索変数を取得"""
        return self.search_var
    
    def update_font(self, ui_font_size, list_font_size):
        """フォントサイズを更新"""
        self.font_size = list_font_size
        self.status_label.configure(font=("", ui_font_size))
        self.assignment_listbox.configure(font=("", list_font_size))
