#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クラス管理関連ダイアログ
"""

import os
import tkinter as tk
from tkinter import ttk


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
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="キャンセル",
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


class EditClassDialog:
    """クラス編集ダイアログ"""
    def __init__(self, parent, current_name):
        self.new_name = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("クラス編集")
        self.dialog.geometry("380x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 190
        y = (self.dialog.winfo_screenheight() // 2) - 100
        self.dialog.geometry(f"380x200+{x}+{y}")
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 説明
        ttk.Label(
            main_frame,
            text=f"現在のクラス名: {current_name}",
            font=("", 10, "bold")
        ).pack(pady=(0, 10))
        
        ttk.Label(
            main_frame,
            text="新しいクラス名を入力してください:"
        ).pack(pady=(0, 5))
        
        # 入力欄
        self.entry = ttk.Entry(main_frame, width=35)
        self.entry.pack(pady=5)
        self.entry.insert(0, current_name)
        self.entry.focus()
        self.entry.select_range(0, tk.END)
        
        # Enterキーでも確定
        self.entry.bind('<Return>', lambda e: self._on_ok())
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="OK",
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
        self.new_name = self.entry.get().strip()
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.new_name = None
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.new_name
