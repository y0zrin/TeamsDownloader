#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
クラス管理ハンドラ
"""

from tkinter import messagebox
from gui.dialogs import EditClassDialog


class ClassHandler:
    """クラス管理ハンドラ"""
    
    def __init__(self, root, assignment_service, state, log_callback, refresh_callback):
        """
        Args:
            root: ルートウィンドウ
            assignment_service: 課題サービス
            state: アプリケーション状態
            log_callback: ログ出力コールバック
            refresh_callback: クラスリスト更新コールバック
        """
        self.root = root
        self.assignment_service = assignment_service
        self.state = state
        self.log = log_callback
        self.refresh_class_list = refresh_callback
    
    def add_class(self):
        """クラスを追加"""
        from tkinter import simpledialog
        
        class_name = simpledialog.askstring(
            "クラス追加",
            "Teams側のチーム名を入力してください。\n（例：OHCxx-AT99A999）",
            parent=self.root
        )
        
        if class_name:
            success, message = self.assignment_service.add_class(class_name)
            if success:
                self.log(message)
                self.refresh_class_list()
            else:
                messagebox.showerror("エラー", message)
    
    def edit_class(self):
        """クラスを編集"""
        classes = self.assignment_service.get_classes()
        current_index = self.state.get_selected_class_index()
        
        if current_index is None:
            messagebox.showwarning("警告", "編集するクラスを選択してください")
            return
        
        current_class = classes[current_index]
        current_name = current_class['name']
        
        # 編集ダイアログを表示
        dialog = EditClassDialog(self.root, current_name)
        new_name = dialog.show()
        
        if new_name and new_name != current_name:
            success, message = self.assignment_service.edit_class(current_name, new_name)
            if success:
                self.log(message)
                self.refresh_class_list()
            else:
                messagebox.showerror("エラー", message)
    
    def delete_class(self):
        """クラスを削除"""
        classes = self.assignment_service.get_classes()
        current_index = self.state.get_selected_class_index()
        
        if current_index is None:
            messagebox.showwarning("警告", "削除するクラスを選択してください")
            return
        
        selected_class = classes[current_index]
        
        if messagebox.askyesno(
            "確認",
            f"クラス「{selected_class['name']}」を削除しますか?"
        ):
            success, message = self.assignment_service.delete_class(selected_class['name'])
            if success:
                self.log(message)
                self.state.set_selected_class_index(None)
                self.refresh_class_list()
            else:
                messagebox.showerror("エラー", message)
