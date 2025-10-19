#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メインGUIウィンドウ（リファクタリング版）

責務:
- ウィンドウ初期化とレイアウト構成
- パネルとハンドラの統合
- 初期化処理
"""

import os
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from core.auth import AuthManager
from core.api_client import GraphAPIClient
from core.cache import AssignmentCache
from services.assignment import AssignmentService
from services.downloader import DownloadService
from services.submission_checker_service import SubmissionCheckerService

from gui.state import AppState
from gui.panels import ClassPanel, AssignmentPanel, LogPanel
from gui.handlers import AuthHandler, ClassHandler, DownloadHandler, SettingsHandler


class TeamsDownloaderGUI:
    """メインGUIウィンドウ"""
    
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
        self.submission_service = SubmissionCheckerService(self.api_client, self.assignment_cache)
        
        # 状態管理
        self.state = AppState()
        
        # フォント設定を読み込み
        self.font_config = self.assignment_cache.get_font_config()
        
        # UIを構築
        self._create_ui()
        
        # ハンドラを初期化
        self._init_handlers()
        
        # ログをリダイレクト
        self.log_panel.redirect_output()
        
        # 初期化処理
        self._initialize()
    
    def _create_ui(self):
        """UI構築"""
        # メインコンテナ
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 上部: 左右分割パネル
        top_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        top_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 左パネル: クラス管理
        left_frame = ttk.LabelFrame(top_paned, text="📚 クラス", padding="10")
        top_paned.add(left_frame, weight=1)
        
        # クラスパネルは後でハンドラ設定後に作成
        self.left_panel_frame = left_frame
        
        # 右パネル: 課題一覧
        right_frame = ttk.LabelFrame(top_paned, text="📝 課題", padding="10")
        top_paned.add(right_frame, weight=2)
        
        # 課題パネルも後でハンドラ設定後に作成
        self.right_panel_frame = right_frame
        
        # 下部: ログエリア
        log_frame = ttk.LabelFrame(main_container, text="📋 ログ", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_panel = LogPanel(log_frame, self.font_config['log'])
    
    def _init_handlers(self):
        """ハンドラ初期化"""
        # 認証ハンドラ
        self.auth_handler = AuthHandler(
            self.root,
            self.auth_manager,
            self.state
        )
        
        # クラスハンドラ
        self.class_handler = ClassHandler(
            self.root,
            self.assignment_service,
            self.state,
            self.log,
            self.refresh_class_list
        )
        
        # 設定ハンドラ（パネル作成前なので一部遅延バインド）
        self.settings_handler = SettingsHandler(
            self.root,
            self.assignment_cache,
            lambda: self.class_panel.get_settings_button(),
            self.log,
            self.apply_font_settings
        )
        
        # ダウンロードハンドラ
        self.download_handler = DownloadHandler(
            self.root,
            {
                'assignment': self.assignment_service,
                'download': self.download_service,
                'submission': self.submission_service,
                'auth': self.auth_manager
            },
            self.state,
            self.assignment_cache,
            self.log,
            {
                'show_download_buttons': lambda: self.assignment_panel.show_download_buttons(),
                'show_cancel_button': lambda: self.assignment_panel.show_cancel_button(),
                'authenticate': self.auth_handler.authenticate_with_gui,
                'get_assignment_selection': lambda: self.assignment_panel.get_listbox().curselection(),
                'get_assignment_name': lambda idx: self.assignment_panel.get_listbox().get(idx)
            }
        )
        
        # パネルを作成（ハンドラが準備できた後）
        self._create_panels()
    
    def _create_panels(self):
        """パネルを作成（ハンドラ準備後）"""
        # クラスパネル
        self.class_panel = ClassPanel(
            self.left_panel_frame,
            self.font_config['list'],
            {
                'add_class': self.class_handler.add_class,
                'edit_class': self.class_handler.edit_class,
                'delete_class': self.class_handler.delete_class,
                'debug_folder': self.download_handler.debug_folder_structure,
                'show_settings': self.settings_handler.show_settings_menu,
                'on_class_select': self.on_class_select
            }
        )
        
        # 課題パネル
        self.assignment_panel = AssignmentPanel(
            self.right_panel_frame,
            self.font_config['list'],
            {
                'refresh': self.refresh_assignments,
                'check_unsubmitted': lambda: self.download_handler.check_unsubmitted(
                    self.assignment_panel.get_listbox()
                ),
                'select_students': lambda: self.download_handler.select_specific_students(
                    self.assignment_panel.get_listbox()
                ),
                'download': lambda: self.download_handler.download_selected_assignment(),
                'cancel_download': self.download_handler.cancel_download,
                'filter': self.filter_assignments
            }
        )
        
        # キーボードショートカット
        self.root.bind('<Shift-Delete>', lambda e: self.settings_handler.clear_cache())
    
    def _initialize(self):
        """初期化処理"""
        self.refresh_class_list()
        self.log("="*60)
        self.log("🚀 アプリケーションを起動しました")
        self.log("="*60)
        
        # キャッシュのバージョンチェック
        self._check_cache_version()
        
        # キャッシュの暗号化状態を表示
        self._show_cache_status()
        
        # 学生情報の読み込み
        self._load_students_info()
        
        # フォント設定を表示
        self._show_font_settings()
        
        # ダウンロード先を表示
        self._show_download_path()
    
    def _check_cache_version(self):
        """キャッシュバージョンチェック"""
        cache_version = self.assignment_cache.cache_data.get('_cache_version', 0)
        if cache_version < 2:
            self.log("")
            self.log("⚠️  重要なお知らせ:")
            self.log("   複数クラス記号を持つ学生に対応しました")
            self.log("   正しく動作させるには、Shift+Del を押してキャッシュをクリアしてください")
            self.log("")
            self.assignment_cache.cache_data['_cache_version'] = 2
            self.assignment_cache.save_cache()
    
    def _show_cache_status(self):
        """キャッシュ状態を表示"""
        from utils.crypto import ENCRYPTION_AVAILABLE
        if ENCRYPTION_AVAILABLE:
            self.log("💾 キャッシュ機能が有効(手動更新まで有効)")
            self.log("🔒 キャッシュは暗号化されています")
        else:
            self.log("💾 キャッシュ機能が有効(手動更新まで有効)")
            self.log("⚠️  暗号化ライブラリ未導入 - キャッシュは平文で保存されます")
            self.log("   (pip install cryptography で暗号化を有効化できます)")
        self.log("")
    
    def _load_students_info(self):
        """学生情報を読み込み"""
        if 'students_info' in self.assignment_cache.cache_data:
            del self.assignment_cache.cache_data['students_info']
            self.assignment_cache.save_cache()
        
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
    
    def _show_font_settings(self):
        """フォント設定を表示"""
        font_size_name = self.assignment_cache.get_font_size()
        size_names = {'smallest': '最小', 'small': '小', 'medium': '中', 'large': '大', 'largest': '最大'}
        self.log(f"🔤 フォントサイズ: {size_names.get(font_size_name, '小')} ({self.font_config['ui']}pt)")
    
    def _show_download_path(self):
        """ダウンロード先を表示"""
        download_path = self.assignment_cache.get_download_path()
        abs_download_path = os.path.abspath(download_path)
        self.log(f"📁 ダウンロード先: {abs_download_path}")
        self.log("")
    
    def log(self, message):
        """ログ出力"""
        self.log_panel.log(message)
    
    def refresh_class_list(self):
        """クラスリストを更新"""
        classes = self.assignment_service.get_classes()
        
        listbox = self.class_panel.get_listbox()
        listbox.delete(0, tk.END)
        
        for cls in classes:
            listbox.insert(tk.END, cls['name'])
    
    def on_class_select(self, event=None):
        """クラス選択時"""
        listbox = self.class_panel.get_listbox()
        selection = listbox.curselection()
        
        if not selection:
            return
        
        self.state.set_selected_class_index(selection[0])
        selected_class = self.assignment_service.get_classes()[selection[0]]
        
        # ステータス更新
        status_label = self.assignment_panel.get_status_label()
        status_label.config(
            text=f"選択中: {selected_class['name']}",
            foreground="blue"
        )
        
        # 課題リストを読み込み
        self.load_assignments(selected_class)
    
    def load_assignments(self, selected_class):
        """課題リストを読み込み"""
        # キャッシュから課題リストを取得
        assignments, last_updated = self.assignment_cache.get(selected_class['name'])
        
        listbox = self.assignment_panel.get_listbox()
        listbox.delete(0, tk.END)
        
        if assignments:
            self.state.all_assignments = assignments
            for assignment in assignments:
                listbox.insert(tk.END, assignment)
            
            # 最終更新時刻を表示
            if last_updated:
                from datetime import datetime
                last_updated_dt = datetime.fromisoformat(last_updated)
                time_str = last_updated_dt.strftime('%m/%d %H:%M')
                status_label = self.assignment_panel.get_status_label()
                status_label.config(
                    text=f"✅ {len(assignments)}個の課題(キャッシュ: {time_str})",
                    foreground="green"
                )
            self.log(f"📝 {len(assignments)}件の課題を読み込みました（キャッシュ）")
        else:
            self.state.all_assignments = []
            status_label = self.assignment_panel.get_status_label()
            status_label.config(
                text="ℹ️ キャッシュなし - 課題を手動更新してください",
                foreground="orange"
            )
            self.log("ℹ️ キャッシュなし - 「🔄 課題を手動更新」をクリックしてください")
    
    def refresh_assignments(self):
        """課題を手動更新"""
        if self.state.get_selected_class_index() is None:
            from tkinter import messagebox
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.state.get_selected_class_index()]
        
        self.log(f"\n🔄 課題を更新中: {selected_class['name']}")
        
        # 認証チェック
        if not self.auth_manager.access_token:
            if not self.auth_handler.authenticate_with_gui():
                return
        
        # 課題をスキャン
        import threading
        from gui.dialogs import ProgressDialog
        
        progress_dialog = ProgressDialog(
            self.root,
            "課題更新中",
            f"「{selected_class['name']}」の課題を更新しています..."
        )
        
        def scan_thread():
            try:
                def progress_callback(msg):
                    self.log(msg)
                    self.root.after(0, lambda m=msg: progress_dialog.update_detail(m))
                
                self.assignment_service.scan_assignments(
                    self.api_client,
                    selected_class,
                    self.assignment_cache,
                    progress_callback=progress_callback
                )
                
                self.root.after(0, lambda: progress_dialog.close())
                self.root.after(0, lambda: self.load_assignments(selected_class))
                
            except Exception as e:
                self.log(f"❌ エラー: {e}")
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda: progress_dialog.close())
        
        thread = threading.Thread(target=scan_thread)
        thread.daemon = True
        thread.start()
    
    def apply_font_settings(self):
        """フォント設定を動的に適用"""
        self.font_config = self.assignment_cache.get_font_config()
        
        # 各パネルのフォントを更新
        self.log_panel.update_font(self.font_config['log'])
        self.class_panel.update_font(self.font_config['list'])
        self.assignment_panel.update_font(self.font_config['ui'], self.font_config['list'])
    
    def filter_assignments(self):
        """検索ボックスの内容で課題をフィルタ"""
        search_text = self.assignment_panel.search_var.get().lower()
        listbox = self.assignment_panel.get_listbox()
        listbox.delete(0, tk.END)
        
        for assignment in self.state.all_assignments:
            if search_text in assignment.lower():
                listbox.insert(tk.END, assignment)
