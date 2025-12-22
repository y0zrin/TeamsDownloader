#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダウンロードハンドラ
"""

import os
import threading
import tkinter as tk
from tkinter import messagebox
from gui.dialogs import (ClassCodeSelectionDialog, UnsubmittedStudentsDialog,
                         SelectStudentsDialog, ProgressDialog, NameMappingDialog,
                         DownloadCompleteDialog)

class DownloadHandler:
    """ダウンロードハンドラ"""
    
    def __init__(self, root, services, state, cache, log_callback, ui_callbacks):
        """
        Args:
            root: ルートウィンドウ
            services: サービス辞書 (assignment_service, download_service, submission_service, auth_manager)
            state: アプリケーション状態
            cache: キャッシュマネージャー
            log_callback: ログ出力コールバック
            ui_callbacks: UI制御コールバック (show_download_buttons, show_cancel_button, authenticate)
        """
        self.root = root
        self.assignment_service = services['assignment']
        self.download_service = services['download']
        self.submission_service = services['submission']
        self.auth_manager = services['auth']
        self.state = state
        self.cache = cache
        self.log = log_callback
        self.ui_callbacks = ui_callbacks
    
    def download_selected_assignment(self, selected_students=None):
        """選択された課題をダウンロード"""
        if self.state.is_downloading():
            self.log("⚠️ ダウンロードが既に実行中です")
            return
        
        if self.state.get_selected_class_index() is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        # 課題選択チェックと課題名取得
        selection = self.ui_callbacks['get_assignment_selection']()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return
        
        assignment_name = self.ui_callbacks['get_assignment_name'](selection[0])
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.state.get_selected_class_index()]
        
        # ダウンロード進行中フラグを設定
        self.state.download_in_progress = True
        
        # キャンセルボタンを表示
        self.ui_callbacks['show_cancel_button']()
        
        # バックグラウンドでダウンロード
        self.state.download_thread = threading.Thread(
            target=self._download_assignment_background,
            args=(selected_class, assignment_name, selected_students)
        )
        self.state.download_thread.daemon = True
        self.state.download_thread.start()

    def cancel_download(self):
        """ダウンロードをキャンセル"""
        if messagebox.askyesno("確認", "ダウンロードをキャンセルしますか?"):
            self.download_service.cancel()
            self.log("⚠️ ダウンロードをキャンセルしました")
    
    def check_unsubmitted(self, assignment_listbox):
        """未提出者を確認"""
        if self.state.get_selected_class_index() is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        selection = assignment_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return
        
        assignment_name = assignment_listbox.get(selection[0])
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.state.get_selected_class_index()]
        
        # プログレスダイアログを表示
        initial_progress_dialog = ProgressDialog(
            self.root,
            "未提出者確認中",
            f"「{assignment_name}」の未提出者を確認しています..."
        )
        
        def fetch_unsubmitted():
            try:
                # 認証チェック
                if not self.auth_manager.access_token:
                    self.root.after(0, lambda: initial_progress_dialog.close())
                    if not self.ui_callbacks['authenticate']():
                        return
                    # 認証後、プログレスダイアログを再表示
                    active_progress_dialog = ProgressDialog(
                        self.root,
                        "未提出者確認中",
                        f"「{assignment_name}」の未提出者を確認しています..."
                    )
                else:
                    # 認証済みの場合は初期ダイアログをそのまま使用
                    active_progress_dialog = initial_progress_dialog
                
                def progress_callback(msg):
                    self.log(msg)
                    if "人" in msg or "個" in msg or "進捗" in msg:
                        self.root.after(0, lambda m=msg: active_progress_dialog.update_detail(m))
                
                unsubmitted_list, error = self.submission_service.get_unsubmitted_students(
                    selected_class,
                    assignment_name,
                    progress_callback=progress_callback
                )
                
                self.root.after(0, lambda: active_progress_dialog.close())
                
                if error:
                    self.root.after(0, lambda: messagebox.showerror("エラー", error))
                    return
                
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
                self.root.after(0, lambda: active_progress_dialog.close())
                self.root.after(0, lambda: messagebox.showerror("エラー", error_msg))
        
        thread = threading.Thread(target=fetch_unsubmitted)
        thread.daemon = True
        thread.start()
    
    def select_specific_students(self, assignment_listbox):
        """特定学生を選択して即座にダウンロード"""
        if self.state.get_selected_class_index() is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        # 課題選択を先にチェックして保存
        selection = assignment_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return
        
        # 選択された課題のインデックスを保存
        selected_assignment_index = selection[0]
        
        students_info = self.cache.get_students_info()
        
        if not students_info:
            messagebox.showwarning(
                "警告",
                "学生情報が見つかりません。\nstudents.csv または students.xlsx を配置してください。"
            )
            return
        
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.state.get_selected_class_index()]
        current_class_name = selected_class['name']
        
        # クラス記号リストをチェック
        class_codes_list = self.cache.get_class_codes(current_class_name)
        if not class_codes_list:
            messagebox.showwarning(
                "警告",
                f"クラス「{current_class_name}」の学生情報が取得できません。\n\n"
                "先に「🔄 課題を手動更新」を実行して、\n"
                "SharePointから学生リストを取得してください。"
            )
            return
        
        dialog = SelectStudentsDialog(self.root, students_info, current_class_name)
        selected_students = dialog.show()
        
        if selected_students:
            # ダイアログから戻った後、課題の選択を復元
            assignment_listbox.selection_clear(0, tk.END)
            assignment_listbox.selection_set(selected_assignment_index)
            assignment_listbox.see(selected_assignment_index)
            
            self.log(f"👥 {len(selected_students)}人を選択してダウンロードを開始")
            self.download_selected_assignment(selected_students)
                
    def _download_assignment_background(self, selected_class, assignment_name, selected_students=None):
        """バックグラウンドでダウンロード実行"""
        try:
            output_folder = self.cache.get_download_path()
            
            # 認証チェック
            if not self.auth_manager.access_token:
                if not self.ui_callbacks['authenticate']():
                    self.root.after(0, self.ui_callbacks['show_download_buttons'])
                    self.root.after(0, self.state.reset_download_state)
                    return
            
            # コールバック定義
            def class_code_dialog_callback(student_name, codes, class_name):
                dialog = ClassCodeSelectionDialog(
                    self.root, student_name, codes, class_name
                )
                return dialog.show()
            
            def name_mapping_dialog_callback(student_name, students_info):
                dialog = NameMappingDialog(self.root, student_name, students_info)
                return dialog.show()
            
            download_count, student_count = self.download_service.download_assignment(
                selected_class,
                assignment_name,
                output_folder,
                progress_callback=self.log,
                class_code_dialog_callback=class_code_dialog_callback,
                selected_students=selected_students,
                name_mapping_dialog_callback=name_mapping_dialog_callback
            )
            
            if not self.download_service.cancelled and student_count > 0:
                from utils.file_utils import sanitize_filename
                safe_assignment_name = sanitize_filename(assignment_name)
                final_folder = os.path.join(output_folder, selected_class['name'], safe_assignment_name)
                
                def show_complete_dialog():
                    dialog = DownloadCompleteDialog(
                        self.root,
                        student_count,
                        download_count,
                        final_folder
                    )
                    dialog.show()
                
                self.root.after(0, show_complete_dialog)
            
            self.root.after(0, self.ui_callbacks['show_download_buttons'])
            self.root.after(0, self.state.reset_download_state)
        
        except Exception as e:
            self.log(f"\n❌ ダウンロードエラー: {e}")
            import traceback
            traceback.print_exc()
            
            self.root.after(0, self.ui_callbacks['show_download_buttons'])
            self.root.after(0, self.state.reset_download_state)
    
    def debug_folder_structure(self):
        """フォルダ構造確認"""
        classes = self.assignment_service.get_classes()
        if not classes:
            messagebox.showwarning("警告", "クラスが登録されていません")
            return
        
        if self.state.get_selected_class_index() is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return
        
        selected_class = classes[self.state.get_selected_class_index()]
        
        initial_progress_dialog = ProgressDialog(
            self.root,
            "フォルダ構造確認中",
            f"「{selected_class['name']}」のフォルダ構造を確認しています..."
        )
        
        def run_debug():
            active_progress_dialog = initial_progress_dialog
            try:
                self.log("\n" + "="*50)
                self.log(f"🔍 フォルダ構造確認: {selected_class['name']}")
                self.log("="*50)
                
                if not self.auth_manager.access_token:
                    self.root.after(0, lambda: initial_progress_dialog.close())
                    if not self.ui_callbacks['authenticate']():
                        return
                    # 認証後、プログレスダイアログを再表示
                    active_progress_dialog = ProgressDialog(
                        self.root,
                        "フォルダ構造確認中",
                        f"「{selected_class['name']}」のフォルダ構造を確認しています..."
                    )
                
                def progress_callback(msg):
                    self.log(msg)
                    if "人" in msg or "個" in msg or "進捗" in msg:
                        self.root.after(0, lambda m=msg: active_progress_dialog.update_detail(m))
                
                from core.api_client import GraphAPIClient
                api_client = GraphAPIClient(self.auth_manager)
                
                self.assignment_service.scan_assignments(
                    api_client,
                    selected_class,
                    self.cache,
                    progress_callback=progress_callback
                )
                
                self.root.after(0, lambda: active_progress_dialog.close())
                
            except Exception as e:
                self.log(f"\n❌ エラー: {e}")
                self.root.after(0, lambda: active_progress_dialog.close())
                
                # ScanErrorの場合はユーザーにエラーを通知
                from services.assignment import ScanError
                if isinstance(e, ScanError):
                    self.root.after(0, lambda: messagebox.showerror("エラー", str(e)))
        
        thread = threading.Thread(target=run_debug)
        thread.daemon = True
        thread.start()
