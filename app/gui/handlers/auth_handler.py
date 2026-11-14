#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
認証ハンドラ
"""

import threading
import time

from gui.dialogs import DeviceCodeDialog
from utils.ui_thread import run_on_main_thread


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
        """GUI付き認証
        
        ワーカースレッドから呼ばれることがあるため、
        ダイアログの生成と待機は必ずメインスレッドで行う。
        """
        auth_result = {'success': False}
        completed = threading.Event()

        def gui_callback(user_code, verification_uri):
            # ダイアログは認証スレッドから呼ばれるのでメインスレッドに依頼する
            def show_dialog():
                self.state.device_code_dialog = DeviceCodeDialog(
                    self.root, user_code, verification_uri
                )
            
            run_on_main_thread(self.root, show_dialog)

        def auth_thread():
            try:
                auth_result['success'] = self.auth_manager.authenticate(
                    gui_callback=gui_callback
                )
            finally:
                completed.set()
                
                # 認証完了後、ダイアログを閉じる
                dialog = self.state.device_code_dialog
                if dialog:
                    self.root.after(0, dialog.close)

        thread = threading.Thread(target=auth_thread)
        thread.daemon = True
        thread.start()

        if threading.current_thread() is threading.main_thread():
            # メインスレッドから呼ばれた場合は、画面を止めないようイベントを回しながら待つ
            while not completed.is_set():
                self.root.update()
                time.sleep(0.05)
        else:
            # ワーカースレッドからはTkに触らずに待つ
            completed.wait()

        return auth_result['success']
