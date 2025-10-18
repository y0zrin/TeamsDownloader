#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メインGUIウィンドウ
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
import threading
import sys
import os
from datetime import datetime

from core.auth import AuthManager
from core.api_client import GraphAPIClient
from core.cache import AssignmentCache
from services.assignment import AssignmentService
from services.downloader import DownloadService
from gui.dialogs import (DeviceCodeDialog, ClassCodeSelectionDialog, 
                         EditClassDialog, UnsubmittedStudentsDialog,
                         SelectStudentsDialog, FontSettingsDialog,
                         ProgressDialog)


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


class TeamsDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Teams課題ダウンローダー")
        self.root.geometry("1000x700")
        
        # サービス層の初期化
        self.auth_manager = AuthManager()
        self.api_client = GraphAPIClient(self.auth_manager)
        self.assignment_cache = AssignmentCache(cache_hours=24)
        self.assignment_service = AssignmentService()
        self.download_service = DownloadService(self.api_client, self.assignment_cache)
        
        # フォント設定を読み込み(新機能2)
        self.font_config = self.assignment_cache.get_font_config()
        
        # デバイスコードダイアログ
        self.device_code_dialog = None
        
        # ダウンロード進行中フラグ(多重起動防止)
        self.download_in_progress = False
        self.download_thread = None
        
        # メインコンテナ
        main_container = ttk.Frame(root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 上部: 左右分割パネル
        top_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        top_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 左パネル: クラス管理
        left_frame = ttk.LabelFrame(top_paned, text="📚 クラス", padding="10")
        top_paned.add(left_frame, weight=1)
        
        self.create_class_panel(left_frame)
        
        # 右パネル: 課題一覧
        right_frame = ttk.LabelFrame(top_paned, text="📝 課題", padding="10")
        top_paned.add(right_frame, weight=2)
        
        self.create_assignment_panel(right_frame)
        
        # 下部: ログエリア
        log_frame = ttk.LabelFrame(main_container, text="📋 ログ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=10,
            state='disabled',
            font=("Consolas", self.font_config['log'])
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # ログのカラータグ
        self.log_text.tag_config("stdout", foreground="black")
        self.log_text.tag_config("stderr", foreground="red")
        
        # 標準出力をリダイレクト
        sys.stdout = TextRedirector(self.log_text, "stdout")
        sys.stderr = TextRedirector(self.log_text, "stderr")
        
        # 初期化
        self.refresh_class_list()
        self.log("="*60)
        self.log("🚀 アプリケーションを起動しました")
        self.log("="*60)
        
        # キャッシュのバージョンチェック(複数クラス記号対応版)
        cache_version = self.assignment_cache.cache_data.get('_cache_version', 0)
        if cache_version < 2:
            self.log("")
            self.log("⚠️  重要なお知らせ:")
            self.log("   複数クラス記号を持つ学生に対応しました")
            self.log("   正しく動作させるには、Shift+Del を押してキャッシュをクリアしてください")
            self.log("")
            # バージョンを更新
            self.assignment_cache.cache_data['_cache_version'] = 2
            self.assignment_cache.save_cache()
        
        # キャッシュの暗号化状態を表示
        from utils.crypto import ENCRYPTION_AVAILABLE
        if ENCRYPTION_AVAILABLE:
            self.log("💾 キャッシュ機能が有効(手動更新まで有効)")
            self.log("🔒 キャッシュは暗号化されています")
        else:
            self.log("💾 キャッシュ機能が有効(手動更新まで有効)")
            self.log("⚠️  暗号化ライブラリ未導入 - キャッシュは平文で保存されます")
            self.log("   (pip install cryptography で暗号化を有効化できます)")
        self.log("")
        
        # students.csv/xlsxの確認
        # 学生情報キャッシュをクリアして最新の情報を読み込む
        if 'students_info' in self.assignment_cache.cache_data:
            del self.assignment_cache.cache_data['students_info']
            self.assignment_cache.save_cache()
        
        # 複数クラス記号を持つ学生のキャッシュを構築
        try:
            multi_class_students = self.assignment_cache.get_multi_class_students()
        except Exception as e:
            self.log(f"⚠️ 複数クラスキャッシュ構築エラー: {e}")
            multi_class_students = {}
        
        try:
            students_info = self.assignment_cache.get_students_info()
            if students_info:
                total_students = len(students_info)
                self.log(f"✅ 学生情報ファイルを読み込みました ({total_students}人)")
                
                if multi_class_students:
                    self.log(f"   📋 複数クラス記号を持つ学生: {len(multi_class_students)}人")
                    for name_key, student_list in multi_class_students.items():
                        codes = [s['class_code'] for s in student_list]
                        self.log(f"      • {student_list[0]['student_name']}: {', '.join(codes)}")
        except Exception as e:
            self.log(f"⚠️ 学生情報読み込みエラー: {e}")
            import traceback
            self.log(traceback.format_exc())
        
        self.log("")
        
        # フォント設定を表示
        font_size_name = self.assignment_cache.get_font_size()
        size_names = {'smallest': '最小', 'small': '小', 'medium': '中', 'large': '大', 'largest': '最大'}
        self.log(f"🔤 フォントサイズ: {size_names.get(font_size_name, '小')} ({self.font_config['ui']}pt)")
        
        # ダウンロード先を表示
        download_path = self.assignment_cache.get_download_path()
        abs_download_path = os.path.abspath(download_path)
        self.log(f"📁 ダウンロード先: {abs_download_path}")
        self.log("")
    
    def create_class_panel(self, parent):
        """左パネル: クラス管理"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        
        # ボタンフレーム
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 1行目のボタン
        button_row1 = ttk.Frame(button_frame)
        button_row1.pack(fill=tk.X, pady=(0, 2))
        
        add_btn = ttk.Button(
            button_row1,
            text="➕ 追加",
            command=self.add_class
        )
        add_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(add_btn, "新しいクラスを追加")
        
        edit_btn = ttk.Button(
            button_row1,
            text="✏️ 編集",
            command=self.edit_class
        )
        edit_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(edit_btn, "選択したクラス名を編集")
        
        delete_btn = ttk.Button(
            button_row1,
            text="🗑️ 削除",
            command=self.delete_class
        )
        delete_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(delete_btn, "選択したクラスを削除")
        
        # 2行目のボタン
        button_row2 = ttk.Frame(button_frame)
        button_row2.pack(fill=tk.X)
        
        structure_btn = ttk.Button(
            button_row2,
            text="📁 構造",
            command=self.debug_folder_structure
        )
        structure_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(structure_btn, "SharePointのフォルダ構造を確認")
        
        settings_btn = ttk.Button(
            button_row2,
            text="⚙️ 設定",
            command=self.show_settings_menu
        )
        settings_btn.pack(side=tk.LEFT, padx=2, expand=True, fill=tk.X)
        ToolTip(settings_btn, "設定メニューを開く")
        
        # 設定メニュー用の参照を保持
        self.settings_button = settings_btn
        
        # クラスリスト
        list_frame = ttk.Frame(parent)
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.class_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", self.font_config['list'])
        )
        self.class_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.class_listbox.yview)
        
        # クラス選択時に課題一覧を更新
        self.class_listbox.bind('<<ListboxSelect>>', self.on_class_selected)
    
    def create_assignment_panel(self, parent):
        """右パネル: 課題一覧"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)
        
        # ステータスラベル
        self.status_label = ttk.Label(
            parent,
            text="← クラスを選択してください",
            foreground="gray",
            font=("", self.font_config['ui'])
        )
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 検索とボタンフレーム
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        control_frame.columnconfigure(1, weight=1)  # 検索欄の列を伸縮可能に
        
        ttk.Label(control_frame, text="🔍").grid(row=0, column=0, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(control_frame, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.search_var.trace('w', self.filter_assignments)
        
        refresh_btn = ttk.Button(
            control_frame,
            text="🔄 最新の課題一覧を取得",
            command=self.refresh_assignments
        )
        refresh_btn.grid(row=0, column=2, padx=(0, 5))
        
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
            font=("", self.font_config['ui'])
        )
        self.assignment_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.assignment_listbox.yview)
        
        # ダブルクリックでダウンロード
        self.assignment_listbox.bind('<Double-Button-1>', lambda e: self.download_selected_assignment())
        
        # 下部ボタンフレーム（従来ヒントがあった場所）
        self.bottom_button_frame = ttk.Frame(parent)
        self.bottom_button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        self.bottom_button_frame.columnconfigure(0, weight=1)
        self.bottom_button_frame.columnconfigure(1, weight=1)
        self.bottom_button_frame.columnconfigure(2, weight=1)
        
        # 通常時の3つのボタン
        self.unsubmitted_btn = ttk.Button(
            self.bottom_button_frame,
            text="📊 未提出者一覧を出力",
            command=self.check_unsubmitted
        )
        self.unsubmitted_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 2))
        
        self.select_students_btn = ttk.Button(
            self.bottom_button_frame,
            text="👥 学生を指定してDL",
            command=self.select_specific_students
        )
        self.select_students_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=2)
        
        self.download_button = ttk.Button(
            self.bottom_button_frame,
            text="📥 一括ダウンロード",
            command=self.download_selected_assignment
        )
        self.download_button.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(2, 0))
        
        # キャンセルボタン（ダウンロード中のみ表示）
        self.cancel_button = ttk.Button(
            self.bottom_button_frame,
            text="❌ ダウンロードをキャンセル",
            command=self.cancel_download
        )
        # 初期状態では非表示
        self.cancel_button.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))
        self.cancel_button.grid_remove()
        
        # キーボードショートカット(Shift+Delも維持)
        self.root.bind('<Shift-Delete>', lambda e: self.clear_cache())
        
        # 課題データ保持
        self.all_assignments = []
        self.current_class_index = None
    
    def show_download_buttons(self):
        """通常の3つのボタンを表示"""
        self.cancel_button.grid_remove()
        self.unsubmitted_btn.grid()
        self.select_students_btn.grid()
        self.download_button.grid()
    
    def show_cancel_button(self):
        """キャンセルボタンのみを表示"""
        self.unsubmitted_btn.grid_remove()
        self.select_students_btn.grid_remove()
        self.download_button.grid_remove()
        self.cancel_button.grid()
    
    def show_settings_menu(self):
        """設定メニューを表示（ダウンロード先設定を追加）"""
        # 設定ボタンの位置を取得
        x = self.settings_button.winfo_rootx()
        y = self.settings_button.winfo_rooty() + self.settings_button.winfo_height()
        
        # ポップアップメニューを作成
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="📁 ダウンロード先設定", command=self.set_download_path)
        menu.add_command(label="🔄 ダウンロード先を初期化", command=self.reset_download_path)
        menu.add_separator()
        menu.add_command(label="🔤 フォント設定", command=self.show_font_settings)
        menu.add_command(label="🧹 キャッシュクリア", command=self.clear_cache)
        
        # メニューを表示
        menu.post(x, y)
    
    def set_download_path(self):
        """ダウンロード先を設定"""
        current_path = self.assignment_cache.get_download_path()
        abs_current_path = os.path.abspath(current_path)
        
        # フォルダ選択ダイアログを表示
        new_path = filedialog.askdirectory(
            title="ダウンロード先フォルダを選択",
            initialdir=abs_current_path
        )
        
        if new_path:
            # 相対パスに変換（可能な場合）
            try:
                # カレントディレクトリからの相対パスを取得
                rel_path = os.path.relpath(new_path, os.getcwd())
                # 相対パスが .. で始まらない場合のみ相対パスを使用
                if not rel_path.startswith('..'):
                    save_path = rel_path
                else:
                    save_path = new_path
            except ValueError:
                # 異なるドライブの場合など
                save_path = new_path
            
            # キャッシュに保存
            self.assignment_cache.set_download_path(save_path)
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
            reset_path = self.assignment_cache.reset_download_path()
            abs_reset_path = os.path.abspath(reset_path)
            self.log(f"🔄 ダウンロード先を初期設定に戻しました: {abs_reset_path}")
            messagebox.showinfo(
                "設定完了",
                f"ダウンロード先を初期設定に戻しました:\n\n{abs_reset_path}"
            )
    
    def apply_font_settings(self):
        """フォント設定を動的に適用(再起動不要)"""
        self.font_config = self.assignment_cache.get_font_config()
        
        # ログエリアのフォント
        self.log_text.configure(font=("Consolas", self.font_config['log']))
        
        # ステータスラベルのフォント
        self.status_label.configure(font=("", self.font_config['ui']))
        
        # クラスリストのフォント
        self.class_listbox.configure(font=("", self.font_config['list']))
        
        # 課題リストのフォント
        self.assignment_listbox.configure(font=("", self.font_config['ui']))
        
        self.log(f"✅ フォント設定を適用しました ({self.font_config['ui']}pt)")
    
    def log(self, message):
        """ログメッセージを表示"""
        print(message)
    
    def refresh_class_list(self):
        """クラスリストを更新"""
        self.class_listbox.delete(0, tk.END)
        for cls in self.assignment_service.get_classes():
            self.class_listbox.insert(tk.END, cls['name'])
    
    def add_class(self):
        """クラスを追加"""
        class_name = simpledialog.askstring(
            "クラス追加",
            "クラス名を入力してください:\n(例: OHC25-AT12B543)",
            parent=self.root
        )
        
        if not class_name or not class_name.strip():
            return
        
        class_name = class_name.strip()
        
        success, message = self.assignment_service.add_class(class_name)
        if not success:
            messagebox.showerror("エラー", message)
        else:
            self.refresh_class_list()
            self.log(message)
    
    def edit_class(self):
        """クラスを編集(新機能1)"""
        selection = self.class_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "編集するクラスを選択してください")
            return
        
        index = selection[0]
        classes = self.assignment_service.get_classes()
        current_name = classes[index]["name"]
        
        # 編集ダイアログを表示
        dialog = EditClassDialog(self.root, current_name)
        new_name = dialog.show()
        
        if new_name and new_name != current_name:
            success, message = self.assignment_service.edit_class(index, new_name)
            if success:
                self.refresh_class_list()
                
                # 編集したクラスを再選択
                self.class_listbox.selection_set(index)
                
                # 課題リストをクリア
                self.assignment_listbox.delete(0, tk.END)
                self.all_assignments.clear()
                self.status_label.config(text="← クラスを選択してください", foreground="gray")
                
                self.log(message)
            else:
                messagebox.showerror("エラー", message)
    
    def delete_class(self):
        """選択されたクラスを削除"""
        selection = self.class_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "削除するクラスを選択してください")
            return
        
        index = selection[0]
        classes = self.assignment_service.get_classes()
        class_name = classes[index]["name"]
        
        if messagebox.askyesno("確認", f"{class_name} を削除しますか?"):
            success, message = self.assignment_service.delete_class(index)
            if success:
                self.refresh_class_list()
                
                # 課題リストをクリア
                self.assignment_listbox.delete(0, tk.END)
                self.all_assignments.clear()
                self.current_class_index = None
                self.status_label.config(text="← クラスを選択してください", foreground="gray")
                
                self.log(message)
            else:
                messagebox.showerror("エラー", message)
    
    def on_class_selected(self, event=None):
        """クラスが選択されたときの処理"""
        selection = self.class_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        self.current_class_index = index
        
        classes = self.assignment_service.get_classes()
        selected_class = classes[index]
        class_name = selected_class['name']
        
        # キャッシュをチェック
        cached_assignments, last_updated = self.assignment_cache.get(class_name)
        if cached_assignments:
            # キャッシュから読み込み
            self.all_assignments = cached_assignments
            self.assignment_listbox.delete(0, tk.END)
            for assignment in cached_assignments:
                self.assignment_listbox.insert(tk.END, assignment)
            
            # 最終更新時刻を表示
            last_updated_dt = datetime.fromisoformat(last_updated)
            time_str = last_updated_dt.strftime('%m/%d %H:%M')
            self.status_label.config(
                text=f"✅ {len(cached_assignments)}個の課題(キャッシュ: {time_str})",
                foreground="green"
            )
            self.log(f"📚 {class_name}: キャッシュから{len(cached_assignments)}個の課題を読み込み")
        else:
            # 課題一覧を取得
            self.load_assignments(force_refresh=False)
    
    def load_assignments(self, force_refresh=False):
        """選択されたクラスの課題一覧を読み込む"""
        if self.current_class_index is None:
            return
        
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.current_class_index]
        class_name = selected_class['name']
        
        # 認証チェック
        if not self.auth_manager.access_token:
            if not self.authenticate_with_gui():
                self.status_label.config(text="❌ 認証がキャンセルされました", foreground="red")
                return
        
        # UIをリセット
        self.assignment_listbox.delete(0, tk.END)
        self.all_assignments.clear()
        self.search_var.set("")
        
        if force_refresh:
            progress_title = "課題スキャン中"
            progress_msg = "最新の課題一覧を取得しています..."
            self.log(f"🔄 {class_name}: 最新の課題一覧を取得中(フルスキャン)...")
        else:
            progress_title = "課題読み込み中"
            progress_msg = "課題一覧を取得しています..."
            self.log(f"📥 {class_name}: 課題一覧を初回取得中...")
        
        # プログレスダイアログを表示
        progress_dialog = ProgressDialog(self.root, progress_title, progress_msg)
        
        # バックグラウンドで課題を取得
        def fetch_assignments():
            try:
                # プログレスバー更新用のコールバック
                def progress_callback(msg):
                    self.log(msg)
                    # 詳細メッセージを更新
                    if "人" in msg or "個" in msg or "進捗" in msg:
                        self.root.after(0, lambda m=msg: progress_dialog.update_detail(m))
                
                sorted_assignments = self.assignment_service.scan_assignments(
                    self.api_client,
                    selected_class,
                    self.assignment_cache,
                    progress_callback=progress_callback
                )
                
                self.all_assignments = sorted_assignments
                
                def update_ui():
                    # プログレスダイアログを閉じる
                    progress_dialog.close()
                    
                    self.assignment_listbox.delete(0, tk.END)
                    for assignment in sorted_assignments:
                        self.assignment_listbox.insert(tk.END, assignment)
                    
                    if sorted_assignments:
                        now_str = datetime.now().strftime('%m/%d %H:%M')
                        self.status_label.config(
                            text=f"✅ {len(sorted_assignments)}個の課題が見つかりました(更新: {now_str})",
                            foreground="green"
                        )
                    else:
                        self.status_label.config(
                            text="⚠️ 課題が見つかりませんでした",
                            foreground="orange"
                        )
                
                self.root.after(0, update_ui)
                
            except Exception as e:
                error_msg = f"❌ エラー: {str(e)}"
                self.log(error_msg)
                
                def show_error():
                    progress_dialog.close()
                    self.status_label.config(
                        text=error_msg,
                        foreground="red"
                    )
                
                self.root.after(0, show_error)
        
        # スレッドで実行
        thread = threading.Thread(target=fetch_assignments)
        thread.daemon = True
        thread.start()
    
    def refresh_assignments(self):
        """課題一覧を強制更新"""
        if self.current_class_index is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        self.load_assignments(force_refresh=True)
    
    def filter_assignments(self, *args):
        """検索ボックスの内容で課題をフィルタ"""
        search_text = self.search_var.get().lower()
        self.assignment_listbox.delete(0, tk.END)
        
        for assignment in self.all_assignments:
            if search_text in assignment.lower():
                self.assignment_listbox.insert(tk.END, assignment)
    
    def check_unsubmitted(self):
        """未提出者を確認(新機能4)"""
        if self.current_class_index is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        selection = self.assignment_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return
        
        assignment_name = self.assignment_listbox.get(selection[0])
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.current_class_index]
        
        # 認証チェック
        if not self.auth_manager.access_token:
            if not self.authenticate_with_gui():
                return
        
        # プログレスダイアログを表示
        progress_dialog = ProgressDialog(
            self.root,
            "未提出者確認中",
            f"「{assignment_name}」の未提出者を確認しています..."
        )
        
        # バックグラウンドで未提出者を取得
        def fetch_unsubmitted():
            try:
                # プログレスバー更新用のコールバック
                def progress_callback(msg):
                    self.log(msg)
                    if "人" in msg or "進捗" in msg:
                        self.root.after(0, lambda m=msg: progress_dialog.update_detail(m))
                
                unsubmitted_list, error = self.download_service.get_unsubmitted_students(
                    selected_class,
                    assignment_name,
                    progress_callback=progress_callback
                )
                
                # プログレスダイアログを閉じる
                self.root.after(0, lambda: progress_dialog.close())
                
                if error:
                    self.root.after(0, lambda: messagebox.showerror("エラー", error))
                    return
                
                # UIスレッドでダイアログを表示
                def show_dialog():
                    if unsubmitted_list:
                        UnsubmittedStudentsDialog(
                            self.root,
                            selected_class['name'],
                            assignment_name,
                            unsubmitted_list
                        )
                    else:
                        messagebox.showinfo(
                            "確認完了",
                            f"未提出者はいません!\n全員提出済みです。"
                        )
                
                self.root.after(0, show_dialog)
                
            except Exception as e:
                error_msg = f"❌ 未提出者確認エラー: {str(e)}"
                self.log(error_msg)
                self.root.after(0, lambda: progress_dialog.close())
                self.root.after(0, lambda: messagebox.showerror("エラー", error_msg))
        
        # スレッドで実行
        thread = threading.Thread(target=fetch_unsubmitted)
        thread.daemon = True
        thread.start()
    
    def select_specific_students(self):
        """特定学生を選択して即座にダウンロード(新機能5)"""
        if self.current_class_index is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        selection = self.assignment_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return
        
        students_info = self.assignment_cache.get_students_info()
        
        if not students_info:
            messagebox.showwarning(
                "警告",
                "学生情報が見つかりません。\nstudents.csv または students.xlsx を配置してください。"
            )
            return
        
        # 現在のクラス名を取得
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.current_class_index]
        current_class_name = selected_class['name']
        
        # 学生選択ダイアログを表示(クラス名を渡す)
        dialog = SelectStudentsDialog(self.root, students_info, current_class_name)
        selected_students = dialog.show()
        
        if selected_students:
            self.log(f"👥 {len(selected_students)}人を選択してダウンロードを開始")
            
            # 選択された課題名を取得
            assignment_name = self.assignment_listbox.get(selection[0])
            classes = self.assignment_service.get_classes()
            selected_class = classes[self.current_class_index]
            
            # 即座にダウンロードを開始
            self.download_in_progress = True
            self.show_cancel_button()
            
            self.download_thread = threading.Thread(
                target=self.download_assignment_background,
                args=(selected_class, assignment_name, selected_students)
            )
            self.download_thread.daemon = True
            self.download_thread.start()
    
    def download_selected_assignment(self):
        """選択された課題をダウンロード"""
        # 既にダウンロード中の場合は何もしない
        if self.download_in_progress:
            self.log("⚠️ ダウンロードが既に実行中です")
            return
        
        if self.current_class_index is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        selection = self.assignment_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return
        
        assignment_name = self.assignment_listbox.get(selection[0])
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.current_class_index]
        
        # ダウンロード進行中フラグを設定
        self.download_in_progress = True
        
        # キャンセルボタンを表示
        self.show_cancel_button()
        
        # バックグラウンドでダウンロード
        self.download_thread = threading.Thread(
            target=self.download_assignment_background,
            args=(selected_class, assignment_name)
        )
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def cancel_download(self):
        """ダウンロードをキャンセル"""
        if messagebox.askyesno("確認", "ダウンロードをキャンセルしますか?"):
            self.download_service.cancel()
            self.log("\n⚠️ ダウンロードをキャンセルしました")
            
            # 通常のボタンを表示
            self.show_download_buttons()
            
            # ダウンロード進行中フラグをリセット
            self.download_in_progress = False
    
    def download_assignment_background(self, selected_class, assignment_name, selected_students=None):
        """課題をバックグラウンドでダウンロード（ダウンロード先設定対応版）"""
        try:
            # 認証
            if not self.auth_manager.access_token:
                self.log("🔐 認証が必要です...")
                if not self.authenticate_with_gui():
                    self.log("❌ 認証がキャンセルされました")
                    return
            
            # ダウンロード処理
            selected_class = self.assignment_service.migrate_old_config(selected_class)
            
            # ダウンロード先をキャッシュから取得
            download_base_path = self.assignment_cache.get_download_path()
            
            # パスの検証と自動修復
            try:
                abs_path = os.path.abspath(download_base_path)
                # パスが存在しない、またはアクセスできない場合
                if not os.path.exists(abs_path):
                    self.log(f"⚠️ ダウンロード先が見つかりません: {abs_path}")
                    # 初期設定に戻す
                    from core.cache import DEFAULT_DOWNLOAD_PATH
                    download_base_path = DEFAULT_DOWNLOAD_PATH
                    self.assignment_cache.reset_download_path()
                    abs_path = os.path.abspath(download_base_path)
                    self.log(f"🔄 初期設定を適用しました: {abs_path}")
                
                # フォルダを作成（必要に応じて）
                os.makedirs(abs_path, exist_ok=True)
                output_folder = abs_path
                
            except (OSError, PermissionError) as e:
                self.log(f"❌ ダウンロード先へのアクセスエラー: {e}")
                # 初期設定に戻す
                from core.cache import DEFAULT_DOWNLOAD_PATH
                download_base_path = DEFAULT_DOWNLOAD_PATH
                self.assignment_cache.reset_download_path()
                output_folder = os.path.abspath(download_base_path)
                os.makedirs(output_folder, exist_ok=True)
                self.log(f"🔄 初期設定を適用しました: {output_folder}")
            
            # クラス記号選択ダイアログのコールバック
            def class_code_dialog_callback(student_name, codes, class_name):
                dialog = ClassCodeSelectionDialog(
                    self.root, student_name, codes, class_name
                )
                return dialog.show()
            
            # ★ 追加: 名前マッピングダイアログのコールバック
            def name_mapping_dialog_callback(student_name, students_info):
                from gui.dialogs import NameMappingDialog
                dialog = NameMappingDialog(self.root, student_name, students_info)
                return dialog.show()

            download_count, student_count = self.download_service.download_assignment(
                selected_class,
                assignment_name,
                output_folder,
                progress_callback=self.log,
                class_code_dialog_callback=class_code_dialog_callback,
                selected_students=selected_students,
                name_mapping_dialog_callback=name_mapping_dialog_callback  # ★ 追加
            )
            
            if not self.download_service.cancelled and student_count > 0:
                # 保存先フォルダを再計算
                from utils.file_utils import sanitize_filename
                safe_assignment_name = sanitize_filename(assignment_name)
                final_folder = os.path.join(output_folder, selected_class['name'], safe_assignment_name)
                
                # カスタムダイアログを表示
                from gui.dialogs import DownloadCompleteDialog
                def show_complete_dialog():
                    dialog = DownloadCompleteDialog(
                        self.root,
                        student_count,
                        download_count,
                        final_folder
                    )
                    dialog.show()
                
                self.root.after(0, show_complete_dialog)
            
            # 通常のボタンを表示
            self.root.after(0, lambda: self.show_download_buttons())
            self.root.after(0, lambda: setattr(self, 'download_in_progress', False))
        
        except Exception as e:
            self.log(f"\n❌ ダウンロードエラー: {e}")
            import traceback
            traceback.print_exc()
            
            # エラー時も通常のボタンを表示
            self.root.after(0, lambda: self.show_download_buttons())
            self.root.after(0, lambda: setattr(self, 'download_in_progress', False))
    
    def authenticate_with_gui(self):
        """GUI付き認証（改良版）"""
        auth_result = {'success': False, 'completed': False}

        def gui_callback(user_code, verification_uri):
            # ダイアログを表示
            self.device_code_dialog = DeviceCodeDialog(self.root, user_code, verification_uri)

        def auth_thread():
            # 別スレッドで認証実行
            result = self.auth_manager.authenticate(gui_callback=gui_callback)
            auth_result['success'] = result
            auth_result['completed'] = True

            # 認証完了後、ダイアログを閉じる
            if self.device_code_dialog:
                self.root.after(0, lambda: self.device_code_dialog.close())

        # 認証スレッドを開始
        thread = threading.Thread(target=auth_thread)
        thread.daemon = True
        thread.start()

        # 認証完了を待つ（ポーリング方式でGUIをブロックしない）
        def wait_for_auth():
            if not auth_result['completed']:
                self.root.after(100, wait_for_auth)  # 100ms後に再チェック

        wait_for_auth()

        # ダイアログが存在する場合は、その終了を待つ
        if self.device_code_dialog and self.device_code_dialog.dialog.winfo_exists():
            self.device_code_dialog.dialog.wait_window()

        # 念のため、まだ完了していない場合は待機
        while not auth_result['completed']:
            self.root.update()
            import time
            time.sleep(0.1)

        return auth_result['success']
    
    def show_font_settings(self):
        """フォント設定を表示(新機能2 - 再起動不要版)"""
        current_size = self.assignment_cache.get_font_size()
        
        dialog = FontSettingsDialog(self.root, current_size)
        new_size = dialog.show()
        
        if new_size and new_size != current_size:
            # 設定を保存
            self.assignment_cache.set_font_size(new_size)
            self.log(f"🔤 フォントサイズを変更しました: {new_size}")
            
            # 即座にフォントを適用
            self.apply_font_settings()
    
    def clear_cache(self):
        """キャッシュをクリア"""
        # キャッシュクリアオプションを提示
        dialog = tk.Toplevel(self.root)
        dialog.title("キャッシュクリア")
        dialog.geometry("400x250")  # ← 高さを200→250に変更
        dialog.transient(self.root)
        dialog.grab_set()
        
        # センタリング
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 200
        y = (dialog.winfo_screenheight() // 2) - 125  # ← -100→-125に変更
        dialog.geometry(f"400x250+{x}+{y}")  # ← 高さを200→250に変更
        
        ttk.Label(
            dialog,
            text="クリアする項目を選択してください:",
            font=("", 10, "bold")
        ).pack(pady=10)
        
        var_all = tk.BooleanVar(value=False)
        var_assignments = tk.BooleanVar(value=False)
        var_students = tk.BooleanVar(value=True)  # デフォルトで選択
        var_selections = tk.BooleanVar(value=False)
        var_mappings = tk.BooleanVar(value=False)  # ← 追加
        
        ttk.Checkbutton(dialog, text="すべてのキャッシュ", variable=var_all).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="課題一覧キャッシュ", variable=var_assignments).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="学生情報キャッシュ (推奨)", variable=var_students).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="クラス記号選択履歴", variable=var_selections).pack(anchor=tk.W, padx=20)
        ttk.Checkbutton(dialog, text="学生IDマッピング", variable=var_mappings).pack(anchor=tk.W, padx=20)  # ← 追加
        
        result = {'confirmed': False}
        
        def on_ok():
            result['confirmed'] = True
            result['all'] = var_all.get()
            result['assignments'] = var_assignments.get()
            result['students'] = var_students.get()
            result['selections'] = var_selections.get()
            result['mappings'] = var_mappings.get()  # ← 追加
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
                self.assignment_cache.clear_all()
                self.log("🗑️ すべてのキャッシュをクリアしました")
            else:
                cleared = []
                
                if result['assignments']:
                    # 課題キャッシュをクリア
                    keys_to_delete = [k for k in self.assignment_cache.cache_data.keys() 
                                     if not k.startswith('students_') and not k.startswith('class_selection_') and not k.startswith('folder_mapping_') and k not in ['font_size', 'download_path', '_cache_version', 'multi_class_students']]  # ← folder_mapping_を除外に追加
                    for key in keys_to_delete:
                        del self.assignment_cache.cache_data[key]
                    cleared.append("課題一覧キャッシュ")
                
                if result['students']:
                    # 学生情報キャッシュをクリア
                    if 'students_info' in self.assignment_cache.cache_data:
                        del self.assignment_cache.cache_data['students_info']
                    cleared.append("学生情報キャッシュ")
                
                if result['selections']:
                    # クラス記号選択履歴をクリア
                    keys_to_delete = [k for k in self.assignment_cache.cache_data.keys() 
                                     if k.startswith('class_selection_')]
                    for key in keys_to_delete:
                        del self.assignment_cache.cache_data[key]
                    cleared.append("クラス記号選択履歴")
                
                if result['mappings']:  # ← 追加
                    # 学生IDマッピングをクリア
                    self.assignment_cache.clear_folder_mappings()
                    cleared.append("学生IDマッピング")
                
                if cleared:
                    self.assignment_cache.save_cache()
                    self.log(f"🗑️ キャッシュをクリアしました: {', '.join(cleared)}")
                else:
                    self.log("ℹ️ クリアする項目が選択されませんでした")
    
    def debug_folder_structure(self):
        """フォルダ構造確認"""
        classes = self.assignment_service.get_classes()
        if not classes:
            messagebox.showwarning("警告", "クラスが登録されていません")
            return
        
        if self.current_class_index is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        selected_class = classes[self.current_class_index]
        
        # プログレスダイアログを表示
        progress_dialog = ProgressDialog(
            self.root,
            "フォルダ構造確認中",
            f"「{selected_class['name']}」のフォルダ構造を確認しています..."
        )
        
        def run_debug():
            try:
                self.log("\n" + "="*50)
                self.log(f"🔍 フォルダ構造確認: {selected_class['name']}")
                self.log("="*50)
                
                # 認証
                if not self.auth_manager.access_token:
                    self.root.after(0, lambda: progress_dialog.close())
                    if not self.authenticate_with_gui():
                        return
                    # 再度プログレスダイアログを表示
                    progress_dialog2 = ProgressDialog(
                        self.root,
                        "フォルダ構造確認中",
                        f"「{selected_class['name']}」のフォルダ構造を確認しています..."
                    )
                else:
                    progress_dialog2 = progress_dialog
                
                # プログレスバー更新用のコールバック
                def progress_callback(msg):
                    self.log(msg)
                    if "人" in msg or "個" in msg or "進捗" in msg:
                        self.root.after(0, lambda m=msg: progress_dialog2.update_detail(m))
                
                # スキャン実行
                self.assignment_service.scan_assignments(
                    self.api_client,
                    selected_class,
                    self.assignment_cache,
                    progress_callback=progress_callback
                )
                
                # 完了
                self.root.after(0, lambda: progress_dialog2.close())
                
            except Exception as e:
                self.log(f"\n❌ エラー: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: progress_dialog.close())
        
        thread = threading.Thread(target=run_debug)
        thread.daemon = True
        thread.start()