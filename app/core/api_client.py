#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Microsoft Graph APIクライアント
"""

import requests


class GraphAPIClient:
    """Graph API通信クラス"""
    
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
    
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
        
        response = requests.get(url, headers=headers)
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
        
        response = requests.get(url, headers=headers)
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
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            # エラーログを表示しないでサイレントに失敗
            return []
    
    def download_file(self, drive_id, file_path, save_path):
        """ファイルをダウンロード"""
        import os
        
        encoded_path = requests.utils.quote(file_path)
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/content"
        headers = self._get_headers()
        
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    
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
            response = requests.get(url, headers=headers)
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

        response = requests.delete(url, headers=headers)

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

        response = requests.delete(url, headers=headers)

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
