#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Microsoft Graph APIクライアント
"""

import os
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter

# 同時接続数（ダウンロード・スキャンの並列数より少し多めに確保）
CONNECTION_POOL_SIZE = 16

# ダウンロードのチャンクサイズ
DOWNLOAD_CHUNK_SIZE = 1024 * 1024

# 通常のAPI呼び出しのタイムアウト (接続, 読み取り)
# 応答が返らないとキャンセルもできなくなるため、必ず上限を設ける
REQUEST_TIMEOUT = (10, 60)

# ファイルダウンロードのタイムアウト (接続, 読み取り)
DOWNLOAD_TIMEOUT = (10, 300)

# Retry-Afterヘッダが長時間を指示してきた場合の待機上限（秒）
# スロットリング時にワーカースレッドが何分も眠るとアプリの終了が遅くなる
MAX_RETRY_AFTER = 15


def _build_retry():
    """429/5xx を自動リトライする設定を作成（Retry-Afterヘッダに従う）"""
    try:
        from urllib3.util.retry import Retry
    except ImportError:
        return None

    class CappedRetry(Retry):
        """Retry-Afterの待機時間に上限を設けたRetry"""

        def get_retry_after(self, response):
            retry_after = super().get_retry_after(response)
            if retry_after is None:
                return None
            return min(retry_after, MAX_RETRY_AFTER)

    kwargs = dict(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    try:
        return CappedRetry(allowed_methods=["GET"], **kwargs)
    except TypeError:
        # urllib3 1.25以前
        return CappedRetry(method_whitelist=["GET"], **kwargs)


class DownloadAborted(Exception):
    """ダウンロード中断（キャンセル）"""


def parse_graph_timestamp(value):
    """Graph APIのISO8601文字列をUNIX時刻に変換（失敗時はNone）"""
    if not value:
        return None
    
    try:
        text = str(value).replace('Z', '+00:00')
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except ValueError:
        return None


class GraphAPIClient:
    """Graph API通信クラス"""
    
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        
        # 接続を使い回してTLSハンドシェイクを省く（1リクエストあたり約0.6秒の短縮）
        self.session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=CONNECTION_POOL_SIZE,
            pool_maxsize=CONNECTION_POOL_SIZE,
            max_retries=_build_retry(),
        )
        self.session.mount("https://", adapter)
    
    def _get_headers(self):
        """認証ヘッダーを取得"""
        token = self.auth_manager.get_token()
        return {"Authorization": f"Bearer {token}"}
    
    def get_site_id(self, site_path):
        """SharePointサイトIDを取得
        
        Returns:
            tuple: (site_id, error_message)
                - 成功時: (site_id, None)
                - 失敗時: (None, error_message)
        """
        # Graph APIのサイトパス形式: /sites/{hostname}:/{relative-path}:
        # 末尾にコロンが必要
        url = f"https://graph.microsoft.com/v1.0/sites/nkzacjp.sharepoint.com:{site_path}:"
        headers = self._get_headers()
        
        response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json()["id"], None
        else:
            # エラーメッセージを生成
            class_name = site_path.replace('/sites/', '')
            if response.status_code == 400:
                error_msg = f"URLが無効です。クラス名 '{class_name}' に不正な文字が含まれている可能性があります"
            elif response.status_code == 404:
                error_msg = f"サイトが見つかりません。クラス名 '{class_name}' が正しいか確認してください"
            elif response.status_code == 401:
                error_msg = "認証が必要です。再ログインしてください"
            elif response.status_code == 403:
                error_msg = "アクセス権がありません"
            else:
                error_msg = f"HTTP {response.status_code}"
            
            print(f"❌ サイトIDの取得に失敗: {response.status_code}")
            print(f"   詳細: {response.text}")
            return None, error_msg
    
    def get_drive_id(self, site_id):
        """ドライブIDを取得"""
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        headers = self._get_headers()
        
        response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            drives = response.json().get("value", [])
            
            # まず "Student Work" ドライブを探す(課題提出用)
            for drive in drives:
                if drive.get("name") == "Student Work":
                    print(f"✅ 'Student Work' ライブラリを発見")
                    return drive["id"], "Student Work"
            
            # 次に "Documents" または "ドキュメント" を探す
            for drive in drives:
                if drive.get("name") in ["Documents", "ドキュメント"]:
                    print(f"✅ '{drive.get('name')}' ライブラリを使用")
                    return drive["id"], drive.get("name")
            
            # 見つからない場合は最初のドライブ
            if drives:
                print(f"✅ '{drives[0].get('name')}' ライブラリを使用")
                return drives[0]["id"], drives[0].get("name")
        else:
            print(f"❌ ドライブIDの取得に失敗: {response.status_code}")
        return None, None
    
    def list_folder_items(self, drive_id, folder_path):
        """フォルダ内のアイテムを一覧取得"""
        encoded_path = requests.utils.quote(folder_path)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/children"
        headers = self._get_headers()
        
        response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            # エラーログを表示しないでサイレントに失敗
            return []
    
    def download_file(self, drive_id, file_path, save_path,
                      last_modified=None, should_cancel=None):
        """ファイルをダウンロード
        
        Args:
            drive_id: ドライブID
            file_path: SharePoint上のファイルパス
            save_path: 保存先パス
            last_modified: SharePoint上の最終更新日時（ISO8601）。
                           保存後にファイルの更新日時として設定し、次回の再DL判定に使う
            should_cancel: キャンセル判定の関数（Trueを返すと中断）
        
        Returns:
            成功したらTrue
        """
        encoded_path = requests.utils.quote(file_path)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/content"
        headers = self._get_headers()
        
        # 途中で失敗したファイルを残さないよう一時ファイルに書く
        temp_path = save_path + ".part"
        
        try:
            with self.session.get(url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
                if response.status_code != 200:
                    return False
                
                directory = os.path.dirname(save_path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if should_cancel and should_cancel():
                            raise DownloadAborted()
                        if chunk:
                            f.write(chunk)
            
            os.replace(temp_path, save_path)
            
            # SharePoint側の更新日時を反映（次回起動時の「更新なし」判定用）
            timestamp = parse_graph_timestamp(last_modified)
            if timestamp:
                try:
                    os.utime(save_path, (timestamp, timestamp))
                except OSError:
                    pass
            
            return True
        
        except DownloadAborted:
            return False
        
        except (requests.RequestException, OSError):
            return False
        
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
    
    def get_student_folders(self, drive_id, base_folder):
        """学生フォルダのリストを取得"""
        student_folders = self.list_folder_items(drive_id, base_folder)
        return [f for f in student_folders if f.get("folder")]
    
    def get_assignment_folders(self, drive_id, student_path):
        """学生フォルダ内の課題フォルダを取得"""
        assignment_folders = self.list_folder_items(drive_id, student_path)
        return [f for f in assignment_folders if f.get("folder")]
    
    def get_files_in_folder(self, drive_id, folder_path):
        """フォルダ内のファイルを取得"""
        items = self.list_folder_items(drive_id, folder_path)
        return [f for f in items if f.get("file")]

    def get_recycle_bin_items(self, site_id):
        """サイトのごみ箱アイテムを一覧取得

        Args:
            site_id: サイトID

        Returns:
            list: ごみ箱アイテムのリスト（失敗時は空リスト）
        """
        items = []
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/recycleBin/items"
        headers = self._get_headers()

        while url:
            response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                items.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
            else:
                print(f"❌ ごみ箱一覧の取得に失敗: {response.status_code}")
                break

        return items

    def purge_recycle_bin_item(self, site_id, item_id):
        """ごみ箱のアイテムを完全削除

        Args:
            site_id: サイトID
            item_id: ごみ箱アイテムのID

        Returns:
            tuple: (success, error_message)
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/recycleBin/items/{item_id}"
        headers = self._get_headers()

        response = self.session.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 204:
            return True, None
        elif response.status_code == 404:
            return True, None  # 既に削除済み
        else:
            return False, f"HTTP {response.status_code}"

    def delete_item(self, drive_id, item_id):
        """ドライブアイテムを削除（ごみ箱に移動）

        Args:
            drive_id: ドライブID
            item_id: 削除するアイテムのID

        Returns:
            tuple: (success, error_message)
                - 成功時: (True, None)
                - 失敗時: (False, error_message)
        """
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}"
        headers = self._get_headers()

        response = self.session.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)

        if response.status_code == 204:
            return True, None
        elif response.status_code == 404:
            return True, None  # 既に削除済み
        elif response.status_code == 403:
            return False, "アクセス権がありません（書き込み権限が必要です）"
        elif response.status_code == 401:
            return False, "認証が切れています。再ログインしてください"
        elif response.status_code == 423:
            return False, "ファイルがロックされています"
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "不明")
            return False, f"レート制限中です（{retry_after}秒後に再試行してください）"
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
