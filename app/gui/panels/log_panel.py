#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログパネル
"""

import sys
import tkinter as tk
from tkinter import ttk, scrolledtext


class TextRedirector:
    """標準出力をテキストウィジェットにリダイレクト"""
    
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, text):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, text, (self.tag,))
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')
        self.widget.update_idletasks()

    def flush(self):
        pass


class LogPanel:
    """ログパネル"""
    
    def __init__(self, parent, font_size):
        self.log_text = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            height=10,
            state='disabled',
            font=("Consolas", font_size)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # ログのカラータグ
        self.log_text.tag_config("stdout", foreground="black")
        self.log_text.tag_config("stderr", foreground="red")
    
    def redirect_output(self):
        """標準出力をリダイレクト"""
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")
    
    def log(self, message):
        """ログメッセージを出力"""
        print(message)
    
    def update_font(self, font_size):
        """フォントサイズを更新"""
        self.log_text.configure(font=("Consolas", font_size))
    
    def get_widget(self):
        """ログテキストウィジェットを取得"""
        return self.log_text
