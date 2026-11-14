#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ログパネル

ログはワーカースレッドからも出力されるため、いったんキューに溜めて
メインスレッドだけがテキストウィジェットへ書き込む。
（Tkをメインスレッド以外から操作するとウィンドウが固まる）
"""

import queue
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext

# ログを画面に反映する間隔（ミリ秒）
PUMP_INTERVAL_MS = 100

# 1回の反映で取り出す最大チャンク数
# 大きすぎると1回の描画が重くなり、画面の反応が鈍る
MAX_CHUNKS_PER_PUMP = 800

# 保持する最大行数（古い行から捨てる）
MAX_LINES = 5000


class TextRedirector:
    """標準出力をログキューに流す

    ここではTkに一切触らない（ワーカースレッドから呼ばれるため）。
    """

    def __init__(self, log_queue, tag="stdout"):
        self.queue = log_queue
        self.tag = tag

    def write(self, text):
        if text:
            self.queue.put((self.tag, text))
        return len(text) if text else 0

    def flush(self):
        pass

    def isatty(self):
        return False


class LogPanel:
    """ログパネル"""
    
    def __init__(self, parent, font_size):
        self.log_queue = queue.Queue()
        self._pumping = False
        
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
        sys.stdout = TextRedirector(self.log_queue, "stdout")
        sys.stderr = TextRedirector(self.log_queue, "stderr")
        self.start_pump()
    
    def start_pump(self):
        """キューの内容を定期的に画面へ反映する"""
        if self._pumping:
            return
        
        self._pumping = True
        self._schedule_pump()
    
    def _schedule_pump(self):
        try:
            self.log_text.after(PUMP_INTERVAL_MS, self._pump)
        except tk.TclError:
            # ウィンドウが閉じられた
            self._pumping = False
    
    def _pump(self):
        """キューの内容を画面へ反映（メインスレッドで実行される）"""
        try:
            self._flush_queue()
        except tk.TclError:
            self._pumping = False
            return
        
        self._schedule_pump()
    
    def _flush_queue(self):
        """溜まったログをまとめて挿入"""
        chunks = []
        
        for _ in range(MAX_CHUNKS_PER_PUMP):
            try:
                chunks.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        
        if not chunks:
            return
        
        self.log_text.configure(state='normal')
        
        # 同じ色が続く部分はまとめて挿入する
        current_tag = chunks[0][0]
        buffer = []
        
        for tag, text in chunks:
            if tag != current_tag:
                self.log_text.insert(tk.END, ''.join(buffer), (current_tag,))
                buffer = []
                current_tag = tag
            buffer.append(text)
        
        self.log_text.insert(tk.END, ''.join(buffer), (current_tag,))
        
        self._trim()
        
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
    
    def _trim(self):
        """古い行を捨てる（行数が増えすぎると描画が重くなる）"""
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        
        if line_count > MAX_LINES:
            self.log_text.delete('1.0', f'{line_count - MAX_LINES + 1}.0')
    
    def log(self, message):
        """ログメッセージを出力（どのスレッドから呼んでもよい）"""
        print(message)
    
    def update_font(self, font_size):
        """フォントサイズを更新"""
        self.log_text.configure(font=("Consolas", font_size))
    
    def get_widget(self):
        """ログテキストウィジェットを取得"""
        return self.log_text
