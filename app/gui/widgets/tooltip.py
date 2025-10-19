#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ツールチップウィジェット
"""

import tkinter as tk


class ToolTip:
    """ツールチップ(マウスオーバーで表示されるヘルプテキスト)"""
    
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.schedule_id = None
        
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
        self.widget.bind("<Button>", self.on_leave)
    
    def on_enter(self, event=None):
        """マウスが入った時"""
        self.schedule_id = self.widget.after(self.delay, self.show_tooltip)
    
    def on_leave(self, event=None):
        """マウスが出た時"""
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None
        self.hide_tooltip()
    
    def show_tooltip(self):
        """ツールチップを表示"""
        if self.tooltip_window:
            return
        
        # マウス位置を取得
        x = self.widget.winfo_pointerx() + 10
        y = self.widget.winfo_pointery() + 10
        
        # ツールチップウィンドウを作成
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # ラベルを作成
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("", 9),
            padx=5,
            pady=3
        )
        label.pack()
    
    def hide_tooltip(self):
        """ツールチップを非表示"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
