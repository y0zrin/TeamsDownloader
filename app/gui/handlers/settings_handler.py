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
    
    def __init__(self, root, assignment_cache, settings_button_ref, log_callback, font_apply_callback, auth_manager=None, api_client=None, authenticate_callback=None):
        """
        Args:
            root: ルートウィンドウ
            assignment_cache: キャッシュマネージャー
            settings_button_ref: 設定ボタンへの参照（callable）
            log_callback: ログ出力コールバック
            font_apply_callback: フォント適用コールバック
            auth_manager: 認証マネージャー
            api_client: GraphAPIクライアント（名簿更新用）
            authenticate_callback: 認証実行コールバック
        """
        self.root = root
        self.cache = assignment_cache
        self.get_settings_button = settings_button_ref
        self.log = log_callback
        self.apply_font_settings = font_apply_callback
        self.auth_manager = auth_manager
        self.api_client = api_client
        self.authenticate = authenticate_callback
    
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
        # ごみ箱を空にする設定（チェックマーク付きトグル）
        empty_recycle = self.cache.get_empty_recycle_bin()
        label = "✅ 削除後にごみ箱を空にする" if empty_recycle else "　 削除後にごみ箱を空にする"
        menu.add_command(label=label, command=self.toggle_empty_recycle_bin)
        menu.add_separator()
        menu.add_command(label="📋 名簿を更新", command=self.update_roster)

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
    
    def toggle_empty_recycle_bin(self):
        """削除後にごみ箱を空にする設定を切り替え"""
        current = self.cache.get_empty_recycle_bin()
        new_value = not current
        self.cache.set_empty_recycle_bin(new_value)
        if new_value:
            self.log("🗑️ 削除後にごみ箱を空にする: ON")
        else:
            self.log("🗑️ 削除後にごみ箱を空にする: OFF")

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

    def update_roster(self):
        """名簿をSharePointから更新"""
        import threading
        from gui.dialogs import ProgressDialog
        from services.roster_updater import RosterUpdater, get_academic_year_semester

        if not self.auth_manager or not self.api_client:
            messagebox.showwarning("警告", "認証情報が設定されていません。")
            return

        # 未認証なら認証を実行
        if not self.auth_manager.get_token():
            if self.authenticate:
                if not self.authenticate():
                    return
            else:
                messagebox.showwarning("警告", "認証されていません。\n先にログインしてください。")
                return

        year, semester = get_academic_year_semester()
        semester_label = "前期" if "前期" in semester else "後期"

        if not messagebox.askyesno(
            "名簿更新",
            f"{year}年度 {semester_label} の名簿をダウンロードしますか？\n\n"
            f"SharePointから最新の名簿ファイルを取得し、\n"
            f"ローカルの学生情報を更新します。"
        ):
            return

        progress_dialog = ProgressDialog(
            self.root,
            "名簿更新中",
            f"{year}年度 {semester_label} の名簿をダウンロード中..."
        )

        def run_update():
            try:
                updater = RosterUpdater(self.api_client)

                def progress(msg):
                    self.log(msg)
                    self.root.after(0, lambda m=msg: progress_dialog.update_detail(m))

                success, message = updater.update_roster(
                    year=year,
                    semester=semester,
                    progress_callback=progress,
                )

                self.root.after(0, lambda: progress_dialog.close())

                if success:
                    self.root.after(0, lambda: messagebox.showinfo("名簿更新完了", message))
                else:
                    self.root.after(0, lambda: messagebox.showwarning("名簿更新", message))

            except Exception as e:
                self.log(f"❌ 名簿更新エラー: {e}")
                self.root.after(0, lambda: progress_dialog.close())
                self.root.after(0, lambda: messagebox.showerror("エラー", str(e)))

        thread = threading.Thread(target=run_update, daemon=True)
        thread.start()
