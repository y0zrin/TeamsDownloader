#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
削除ハンドラ
"""

import threading
from tkinter import messagebox
from gui.dialogs import DeleteConfirmDialog, DeleteCompleteDialog, ProgressDialog


class DeleteHandler:
    """削除ハンドラ"""

    def __init__(self, root, services, state, cache, log_callback, ui_callbacks):
        """
        Args:
            root: ルートウィンドウ
            services: サービス辞書 (assignment, delete, auth)
            state: アプリケーション状態
            cache: キャッシュマネージャー
            log_callback: ログ出力コールバック
            ui_callbacks: UI制御コールバック
        """
        self.root = root
        self.assignment_service = services['assignment']
        self.delete_service = services['delete']
        self.auth_manager = services['auth']
        self.state = state
        self.cache = cache
        self.log = log_callback
        self.ui_callbacks = ui_callbacks

    def delete_selected_assignment(self):
        """選択された課題をSharePointから削除"""
        if self.state.is_busy():
            self.log("⚠️ 他の操作が実行中です")
            return

        if self.state.get_selected_class_index() is None:
            messagebox.showwarning("警告", "クラスを選択してください")
            return

        # 課題選択チェック
        selection = self.ui_callbacks['get_assignment_selection']()
        if not selection:
            messagebox.showwarning("警告", "課題を選択してください")
            return

        assignment_name = self.ui_callbacks['get_assignment_name'](selection[0])
        classes = self.assignment_service.get_classes()
        selected_class = classes[self.state.get_selected_class_index()]

        # 確認ダイアログ（課題名入力必須）
        confirm_dialog = DeleteConfirmDialog(
            self.root, selected_class['name'], assignment_name,
            empty_recycle_bin=self.cache.get_empty_recycle_bin(),
        )
        if not confirm_dialog.show():
            return

        # 削除進行中フラグを設定
        self.state.delete_in_progress = True

        # キャンセルボタンを表示
        self.ui_callbacks['show_cancel_button']()

        # バックグラウンドで削除
        self.state.delete_thread = threading.Thread(
            target=self._delete_assignment_background,
            args=(selected_class, assignment_name),
        )
        self.state.delete_thread.daemon = True
        self.state.delete_thread.start()

    def cancel_delete(self):
        """削除をキャンセル"""
        if messagebox.askyesno("確認", "削除をキャンセルしますか?"):
            self.delete_service.cancel()
            self.log("⚠️ 削除をキャンセルしました")

    def _delete_assignment_background(self, selected_class, assignment_name):
        """バックグラウンドで削除実行"""
        try:
            # 認証チェック
            if not self.auth_manager.access_token:
                if not self.ui_callbacks['authenticate']():
                    self.root.after(0, self.ui_callbacks['show_download_buttons'])
                    self.root.after(0, self.state.reset_delete_state)
                    return

            result = self.delete_service.delete_assignment(
                selected_class,
                assignment_name,
                progress_callback=self.log,
            )

            # 完了ダイアログ表示
            if result.success_count > 0 or result.fail_count > 0:
                def show_complete():
                    dialog = DeleteCompleteDialog(self.root, result)
                    dialog.show()
                self.root.after(0, show_complete)

            # 課題リストを再読み込み
            self.root.after(0, lambda: self.ui_callbacks['refresh_assignments']())

        except Exception as e:
            self.log(f"\n❌ 削除エラー: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.root.after(0, self.ui_callbacks['show_download_buttons'])
            self.root.after(0, self.state.reset_delete_state)
