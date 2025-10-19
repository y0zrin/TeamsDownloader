#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証ハンドラ
"""

import threading
from gui.dialogs import DeviceCodeDialog


class AuthHandler:
    """認証ハンドラ"""
    
    def __init__(self, root, auth_manager, state):
        """
        Args:
            root: ルートウィンドウ
            auth_manager: 認証マネージャー
            state: アプリケーション状態
        """
        self.root = root
        self.auth_manager = auth_manager
        self.state = state
    
    def authenticate_with_gui(self):
        """GUI付き認証"""
        auth_result = {'success': False, 'completed': False}

        def gui_callback(user_code, verification_uri):
            # ダイアログを表示
            self.state.device_code_dialog = DeviceCodeDialog(
                self.root, user_code, verification_uri
            )

        def auth_thread():
            # 別スレッドで認証実行
            result = self.auth_manager.authenticate(gui_callback=gui_callback)
            auth_result['success'] = result
            auth_result['completed'] = True

            # 認証完了後、ダイアログを閉じる
            if self.state.device_code_dialog:
                self.root.after(0, lambda: self.state.device_code_dialog.close())

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
        if self.state.device_code_dialog and self.state.device_code_dialog.dialog.winfo_exists():
            self.state.device_code_dialog.dialog.wait_window()

        # 念のため、まだ完了していない場合は待機
        while not auth_result['completed']:
            self.root.update()
            import time
            time.sleep(0.1)

        return auth_result['success']
