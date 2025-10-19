#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダイアログ共通ユーティリティ
"""

import tkinter as tk


def center_dialog(dialog, width, height):
    """ダイアログを画面中央に配置
    
    Args:
        dialog: tkinter.Toplevel
        width: ダイアログの幅
        height: ダイアログの高さ
    """
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")


def create_centered_dialog(parent, title, width, height, modal=True):
    """中央配置されたダイアログを作成
    
    Args:
        parent: 親ウィンドウ
        title: ダイアログタイトル
        width: 幅
        height: 高さ
        modal: モーダルダイアログにするか
    
    Returns:
        tk.Toplevel
    """
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.geometry(f"{width}x{height}")
    
    if modal:
        dialog.transient(parent)
        dialog.grab_set()
    
    center_dialog(dialog, width, height)
    
    return dialog
