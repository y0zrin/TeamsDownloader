#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定関連ダイアログ（リファクタリング版）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from gui.dialogs.dialog_utils import create_centered_dialog
from utils.exclusion import SUGGESTED_PATTERNS, normalize_pattern, normalize_patterns


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


class ExcludeSettingsDialog:
    """ダウンロード除外設定ダイアログ"""
    def __init__(self, parent, current_patterns=None):
        self.patterns = None
        self._patterns = list(current_patterns or [])
        self.dialog = create_centered_dialog(parent, "ダウンロード除外設定", 520, 620)
        
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        ttk.Label(
            main_frame,
            text="🚫 ダウンロード除外設定",
            font=("", 12, "bold")
        ).pack()
        
        ttk.Label(
            main_frame,
            text="ファイル名がパターンに一致したファイルはダウンロードしません。",
            font=("", 9)
        ).pack(pady=(8, 0))
        
        ttk.Label(
            main_frame,
            text="⚠️ zipファイルの中身は対象外です（zipは1ファイルとして転送されるため）",
            font=("", 9),
            foreground="red",
            wraplength=470,
            justify=tk.LEFT
        ).pack(pady=(4, 10))
        
        # 入力欄
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.entry_var = tk.StringVar()
        entry = ttk.Entry(input_frame, textvariable=self.entry_var, font=("", 10))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind('<Return>', lambda e: self._add_pattern())
        entry.focus()
        
        ttk.Button(
            input_frame,
            text="追加",
            command=self._add_pattern,
            width=8
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(
            main_frame,
            text="例: *.mp4 （拡張子だけ書くと自動で * を補います）",
            font=("", 9),
            foreground="gray"
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # 現在のパターン
        ttk.Label(main_frame, text="現在の除外パターン:", font=("", 10)).pack(anchor=tk.W)
        
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 5))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", 10),
            height=7,
            selectmode=tk.EXTENDED
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        self.listbox.bind('<Delete>', lambda e: self._remove_selected())
        
        remove_frame = ttk.Frame(main_frame)
        remove_frame.pack(fill=tk.X)
        
        ttk.Button(
            remove_frame,
            text="削除",
            command=self._remove_selected,
            width=10
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            remove_frame,
            text="すべて削除",
            command=self._remove_all,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # 候補
        ttk.Label(
            main_frame,
            text="よく使う候補（ダブルクリックで追加）:",
            font=("", 10)
        ).pack(anchor=tk.W, pady=(12, 0))
        
        suggest_frame = ttk.Frame(main_frame)
        suggest_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        suggest_scroll = ttk.Scrollbar(suggest_frame)
        suggest_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.suggest_listbox = tk.Listbox(
            suggest_frame,
            yscrollcommand=suggest_scroll.set,
            font=("", 10),
            height=6
        )
        self.suggest_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        suggest_scroll.config(command=self.suggest_listbox.yview)
        
        for pattern, description in SUGGESTED_PATTERNS:
            self.suggest_listbox.insert(tk.END, f"{pattern}  －  {description}")
        
        self.suggest_listbox.bind('<Double-Button-1>', lambda e: self._add_suggested())
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=12, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="保存",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        self._refresh_list()
    
    def _refresh_list(self):
        """パターン一覧を再描画"""
        self.listbox.delete(0, tk.END)
        for pattern in self._patterns:
            self.listbox.insert(tk.END, pattern)
    
    def _append(self, raw_pattern):
        """パターンを追加（重複は無視）"""
        pattern = normalize_pattern(raw_pattern)
        if not pattern:
            return False
        
        if any(pattern.lower() == p.lower() for p in self._patterns):
            return False
        
        self._patterns.append(pattern)
        self._refresh_list()
        return True
    
    def _add_pattern(self):
        """入力欄のパターンを追加"""
        value = self.entry_var.get().strip()
        if not value:
            return
        
        if self._append(value):
            self.entry_var.set("")
        else:
            messagebox.showinfo("追加できません", "既に登録されているパターンです", parent=self.dialog)
    
    def _add_suggested(self):
        """候補から追加"""
        selection = self.suggest_listbox.curselection()
        if not selection:
            return
        
        pattern = SUGGESTED_PATTERNS[selection[0]][0]
        self._append(pattern)
    
    def _remove_selected(self):
        """選択したパターンを削除"""
        selection = self.listbox.curselection()
        if not selection:
            return
        
        for idx in sorted(selection, reverse=True):
            del self._patterns[idx]
        
        self._refresh_list()
    
    def _remove_all(self):
        """すべて削除"""
        if not self._patterns:
            return
        
        if messagebox.askyesno("確認", "除外パターンをすべて削除しますか？", parent=self.dialog):
            self._patterns = []
            self._refresh_list()
    
    def _on_ok(self):
        # 入力途中のパターンも取り込む
        if self.entry_var.get().strip():
            self._append(self.entry_var.get())
        
        self.patterns = normalize_patterns(self._patterns)
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.patterns = None
        self.dialog.destroy()
    
    def show(self):
        """ダイアログを表示して結果を返す（キャンセル時はNone）"""
        self.dialog.wait_window()
        return self.patterns
