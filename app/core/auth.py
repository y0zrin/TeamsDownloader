#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Microsoft認証管理
"""

import os
import json
import msal
import webbrowser

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


DEFAULT_CLIENT_ID = "1950a258-227b-4e31-a9cf-717495945fc2"
AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPES = ["https://graph.microsoft.com/.default"]
AUTH_CONFIG_FILE = "auth_config.json"


def load_client_id():
    """認証設定ファイルからクライアントIDを読み込む"""
    if os.path.exists(AUTH_CONFIG_FILE):
        try:
            with open(AUTH_CONFIG_FILE, 'r', encoding='utf-8') as f:
                auth_config = json.load(f)
                return auth_config.get("client_id", DEFAULT_CLIENT_ID)
        except:
            pass
    return DEFAULT_CLIENT_ID


class AuthManager:
    """認証管理クラス"""
    
    def __init__(self):
        self.access_token = None
        client_id = load_client_id()
        
        # トークンキャッシュを設定
        self.token_cache = msal.SerializableTokenCache()
        self.cache_file = "token_cache.bin"
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    self.token_cache.deserialize(f.read())
            except:
                pass
        
        self.app = msal.PublicClientApplication(
            client_id,
            authority=AUTHORITY,
            token_cache=self.token_cache
        )
    
    def authenticate(self, gui_callback=None):
        """認証を実行
        
        Args:
            gui_callback: GUI用のコールバック関数 (user_code, verification_uri) を受け取る
        
        Returns:
            bool: 認証成功したかどうか
        """
        # まずキャッシュからトークンを取得試行
        accounts = self.app.get_accounts()
        if accounts:
            print("\n🔑 保存された認証情報を使用中...")
            result = self.app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self.access_token = result["access_token"]
                print("✅ 認証成功(キャッシュ)")
                return True
        
        # キャッシュにトークンがない場合は新規認証
        print("\n=== Microsoft認証 ===")
        print("ブラウザで認証を行います(多要素認証対応)")
        
        # デバイスコードフローを開始
        flow = self.app.initiate_device_flow(scopes=SCOPES)
        
        if "user_code" not in flow:
            print("❌ 認証フローの開始に失敗しました")
            return False
        
        user_code = flow["user_code"]
        verification_uri = flow["verification_uri"]
        
        # GUI用コールバックがあれば呼び出す
        if gui_callback:
            gui_callback(user_code, verification_uri)
        else:
            # CLIモード
            if CLIPBOARD_AVAILABLE:
                try:
                    pyperclip.copy(user_code)
                    print(f"\n✅ 認証コード: {user_code}")
                    print("   (自動的にクリップボードにコピーしました)")
                except:
                    print(f"\n認証コード: {user_code}")
            else:
                print(f"\n認証コード: {user_code}")
                print("   (pyperclipをインストールすると自動コピーされます)")
            
            print(f"\nブラウザで {verification_uri} を開いて、")
            print("このコードを入力してください。")
            print("\n自動的にブラウザが開きます...")
            
            # ブラウザを自動で開く
            try:
                webbrowser.open(verification_uri)
            except:
                print("ブラウザを自動で開けませんでした。")
                print(f"手動で開いてください: {verification_uri}")
        
        # 認証完了を待つ
        result = self.app.acquire_token_by_device_flow(flow)
        
        if "access_token" in result:
            self.access_token = result["access_token"]
            
            # トークンキャッシュを保存
            if self.token_cache.has_state_changed:
                with open(self.cache_file, "w") as f:
                    f.write(self.token_cache.serialize())
            
            print("\n✅ 認証成功!(次回から認証をスキップできます)")
            return True
        else:
            print(f"\n❌ 認証失敗: {result.get('error_description', '不明なエラー')}")
            return False
    
    def get_token(self):
        """アクセストークンを取得"""
        return self.access_token
