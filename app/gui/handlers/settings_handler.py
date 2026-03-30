#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設定ハンドラ
"""

import os
import tkinter as tk
from tkinter import messagebox, filedialog
from gui.dialogs import FontSettingsDialog


class SettingsHandler:
    """設定ハンドラ"""
    
    def __init__(self, root, assignment_cache, settings_button_ref, log_callback, font_apply_callback, auth_manager=None):
        """
        Args:
            root: ルートウィンドウ
            assignment_cache: キャッシュマネージャー
            settings_button_ref: 設定ボタンへの参照（callable）
            log_callback: ログ出力コールバック
            font_apply_callback: フォント適用コールバック
            auth_manager: 認証マネージャー（権限確認用）
        """
        self.root = root
        self.cache = assignment_cache
        self.get_settings_button = settings_button_ref
        self.log = log_callback
        self.apply_font_settings = font_apply_callback
        self.auth_manager = auth_manager
    
    def show_settings_menu(self):
        """設定メニューを表示"""
        # 設定ボタンの位置を取得
        settings_button = self.get_settings_button()
        x = settings_button.winfo_rootx()
        y = settings_button.winfo_rooty() + settings_button.winfo_height()
        
        # ポップアップメニューを作成
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="📁 ダウンロード先設定", command=self.set_download_path)
        menu.add_command(label="🔄 ダウンロード先を初期化", command=self.reset_download_path)
        menu.add_separator()
        menu.add_command(label="🔤 フォント設定", command=self.show_font_settings)
        menu.add_command(label="🧹 キャッシュクリア", command=self.clear_cache)
        menu.add_separator()
        menu.add_command(label="🔑 アクセス権限を確認", command=self.check_permissions)

        # メニューを表示
        menu.post(x, y)
    
    def set_download_path(self):
        """ダウンロード先を設定"""
        current_path = self.cache.get_download_path()
        abs_current_path = os.path.abspath(current_path)
        
        # フォルダ選択ダイアログを表示
        new_path = filedialog.askdirectory(
            title="ダウンロード先フォルダを選択",
            initialdir=abs_current_path
        )
        
        if new_path:
            # 相対パスに変換（可能な場合）
            try:
                rel_path = os.path.relpath(new_path, os.getcwd())
                if not rel_path.startswith('..'):
                    save_path = rel_path
                else:
                    save_path = new_path
            except ValueError:
                save_path = new_path
            
            # キャッシュに保存
            self.cache.set_download_path(save_path)
            abs_save_path = os.path.abspath(save_path)
            self.log(f"📁 ダウンロード先を変更しました: {abs_save_path}")
            messagebox.showinfo(
                "設定完了",
                f"ダウンロード先を変更しました:\n\n{abs_save_path}"
            )
    
    def reset_download_path(self):
        """ダウンロード先を初期設定に戻す"""
        if messagebox.askyesno(
            "確認",
            "ダウンロード先を初期設定に戻しますか?\n\n初期設定: ../ (アプリケーションの親フォルダ)"
        ):
            reset_path = self.cache.reset_download_path()
            abs_reset_path = os.path.abspath(reset_path)
            self.log(f"🔄 ダウンロード先を初期設定に戻しました: {abs_reset_path}")
            messagebox.showinfo(
                "設定完了",
                f"ダウンロード先を初期設定に戻しました:\n\n{abs_reset_path}"
            )
    
    def show_font_settings(self):
        """フォント設定を表示"""
        current_size = self.cache.get_font_size()
        
        dialog = FontSettingsDialog(self.root, current_size)
        new_size = dialog.show()
        
        if new_size and new_size != current_size:
            self.cache.set_font_size(new_size)
            self.log(f"🔤 フォントサイズを変更しました: {new_size}")
            self.apply_font_settings()
    
    def clear_cache(self):
        """キャッシュをクリア"""
        dialog = tk.Toplevel(self.root)
        dialog.title("キャッシュクリア")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # センタリング
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 200
        y = (dialog.winfo_screenheight() // 2) - 125
        dialog.geometry(f"400x250+{x}+{y}")
        
        from tkinter import ttk
        ttk.Label(
            dialog,
            text="クリアする項目を選択してください:",
            font=("", 10, "bold")
        ).pack(pady=10)
        
        var_all = tk.BooleanVar(value=False)
        var_assignments = tk.BooleanVar(value=False)
        var_students = tk.BooleanVar(value=True)
        var_selections = tk.BooleanVar(value=False)
        var_mappings = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(dialog, text="すべてのキャッシュ", variable=var_all).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="課題一覧キャッシュ", variable=var_assignments).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="学生情報キャッシュ (推奨)", variable=var_students).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="クラス記号選択履歴", variable=var_selections).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="学生IDマッピング", variable=var_mappings).pack(anchor=tk.W, padx=20)
        
        result = {'confirmed': False}
        
        def on_ok():
            result['confirmed'] = True
            result['all'] = var_all.get()
            result['assignments'] = var_assignments.get()
            result['students'] = var_students.get()
            result['selections'] = var_selections.get()
            result['mappings'] = var_mappings.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="キャンセル", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        
        if result['confirmed']:
            if result['all']:
                self.cache.clear_all()
                self.log("🗑️ すべてのキャッシュをクリアしました")
            else:
                cleared = []
                
                if result['assignments']:
                    keys_to_delete = [k for k in self.cache.cache_data.keys() 
                                     if not k.startswith('students_') and not k.startswith('class_selection_') and not k.startswith('folder_mapping_') and k not in ['font_size', 'download_path', '_cache_version', 'multi_class_students']]
                    for key in keys_to_delete:
                        del self.cache.cache_data[key]
                    cleared.append("課題一覧キャッシュ")
                
                if result['students']:
                    if 'students_info' in self.cache.cache_data:
                        del self.cache.cache_data['students_info']
                    cleared.append("学生情報キャッシュ")
                
                if result['selections']:
                    keys_to_delete = [k for k in self.cache.cache_data.keys() 
                                     if k.startswith('class_selection_')]
                    for key in keys_to_delete:
                        del self.cache.cache_data[key]
                    cleared.append("クラス記号選択履歴")
                
                if result['mappings']:
                    self.cache.clear_folder_mappings()
                    cleared.append("学生IDマッピング")
                
                if cleared:
                    self.cache.save_cache()
                    self.log(f"🗑️ キャッシュをクリアしました: {', '.join(cleared)}")
                else:
                    self.log("ℹ️ クリアする項目が選択されませんでした")

    def check_permissions(self):
        """アクセストークンの権限を確認"""
        if not self.auth_manager:
            messagebox.showwarning("警告", "認証マネージャーが設定されていません。")
            return

        token = self.auth_manager.get_token()
        if not token:
            messagebox.showwarning("警告", "認証されていません。\n先にログインしてください。")
            return

        from utils.permission_checker import check_token_permissions
        from gui.dialogs import PermissionCheckDialog

        result = check_token_permissions(token)
        dialog = PermissionCheckDialog(self.root, result)
        dialog.show()
