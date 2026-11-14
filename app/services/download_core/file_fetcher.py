#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファイル取得とダウンロード
"""

import os
from typing import List, NamedTuple, Tuple
from models.student import Student
from models.download_result import DownloadedFile
from utils.file_utils import sanitize_filename
from utils.exclusion import match_pattern
from utils.submission_filter import select_latest_files, select_latest_folder
from core.api_client import parse_graph_timestamp

# 更新日時の比較誤差（秒）
MTIME_TOLERANCE = 2


class Submission(NamedTuple):
    """学生1人分の提出物"""
    files: List[dict] = []              # ダウンロード対象のファイル
    path: str = ""                      # 課題フォルダのパス
    old_files: List[tuple] = []         # [(旧版ファイル, 代わりに残した最新ファイル), ...]
    other_folders: List[dict] = []      # 課題名に一致した他のフォルダ


class FileFetcher:
    """ファイル取得クラス"""
    
    def __init__(self, api_client, exclude_patterns=None, should_cancel=None,
                 latest_only=True):
        """
        Args:
            api_client: GraphAPIクライアント
            exclude_patterns: ダウンロード除外パターン（ファイル名のglob）
            should_cancel: キャンセル判定の関数（Trueを返すとダウンロードを中断）
            latest_only: 最新の提出物のみ取得するか
        """
        self.api_client = api_client
        self.exclude_patterns = exclude_patterns or []
        self.should_cancel = should_cancel
        self.latest_only = latest_only
    
    @staticmethod
    def is_up_to_date(save_path: str, file_item: dict) -> bool:
        """ローカルのファイルがSharePoint上のものと同じか判定
        
        サイズが一致し、かつローカルの更新日時がSharePoint側と同じか新しければ
        ダウンロード済みとみなす（再提出されたファイルは落とし直される）。
        """
        size = file_item.get("size")
        if size is None or not os.path.exists(save_path):
            return False
        
        try:
            if os.path.getsize(save_path) != size:
                return False
            local_mtime = os.path.getmtime(save_path)
        except OSError:
            return False
        
        remote_mtime = parse_graph_timestamp(file_item.get("lastModifiedDateTime"))
        if remote_mtime is None:
            return True
        
        return local_mtime >= remote_mtime - MTIME_TOLERANCE
    
    def download_file_item(
        self,
        drive_id: str,
        assignment_path: str,
        file_item: dict,
        output_folder: str
    ) -> DownloadedFile:
        """ファイル1個をダウンロード（除外・ダウンロード済みの判定つき）"""
        file_name = file_item["name"]
        save_path = os.path.join(output_folder, file_name)
        
        # 除外パターンに一致するファイルは転送せずにスキップ
        pattern = match_pattern(file_name, self.exclude_patterns)
        if pattern:
            return DownloadedFile(
                file_name=file_name,
                file_path=save_path,
                success=False,
                skipped=True,
                skip_reason=pattern
            )
        
        # 既にダウンロード済みなら転送しない
        if self.is_up_to_date(save_path, file_item):
            return DownloadedFile(
                file_name=file_name,
                file_path=save_path,
                success=True,
                reused=True
            )
        
        success = self.api_client.download_file(
            drive_id,
            f"{assignment_path}/{file_name}",
            save_path,
            last_modified=file_item.get("lastModifiedDateTime"),
            should_cancel=self.should_cancel
        )
        
        return DownloadedFile(
            file_name=file_name,
            file_path=save_path,
            success=success,
            error=None if success else "ダウンロード失敗"
        )
    
    def fetch_assignment_files(
        self,
        drive_id: str,
        student_folder_path: str,
        assignment_name: str
    ) -> Submission:
        """学生の課題フォルダ内のファイルを取得
        
        latest_only が有効な場合、課題名に一致するフォルダが複数あれば最新のものを選び、
        フォルダ内も拡張子ごとに最新の1件だけを対象にする。
        
        Args:
            drive_id: ドライブID
            student_folder_path: 学生フォルダのパス
            assignment_name: 課題名
        
        Returns:
            Submission
        """
        # 学生フォルダ内の課題フォルダを検索
        assignment_folders = self.api_client.get_assignment_folders(drive_id, student_folder_path)
        
        # 課題名で絞り込み
        search_name = assignment_name.replace('/', '_').lower()
        matched = [
            folder for folder in assignment_folders
            if search_name in folder["name"].lower()
        ]
        
        if not matched:
            return Submission()
        
        # 複数一致した場合の選択
        if self.latest_only:
            folder = select_latest_folder(matched)
        else:
            folder = matched[0]
        
        other_folders = [f for f in matched if f is not folder]
        
        assignment_path = f"{student_folder_path}/{folder['name']}"
        files = self.api_client.get_files_in_folder(drive_id, assignment_path)
        
        # 拡張子ごとに最新の1件だけを残す
        old_files = []
        if self.latest_only and files:
            files, old_files = select_latest_files(files)
        
        return Submission(files, assignment_path, old_files, other_folders)
    
    def download_files(
        self,
        drive_id: str,
        assignment_path: str,
        files: List[dict],
        output_folder: str
    ) -> List[DownloadedFile]:
        """ファイルをダウンロード
        
        Args:
            drive_id: ドライブID
            assignment_path: 課題フォルダのパス
            files: ファイルリスト
            output_folder: 出力フォルダ
        
        Returns:
            ダウンロード結果のリスト
        """
        return [
            self.download_file_item(drive_id, assignment_path, file_item, output_folder)
            for file_item in files
        ]
    
    def create_output_folder(
        self,
        base_folder: str,
        class_name: str,
        assignment_name: str,
        student_info: Student = None,
        sharepoint_name: str = None
    ) -> str:
        """出力フォルダを作成
        
        Args:
            base_folder: ベースフォルダ
            class_name: クラス名
            assignment_name: 課題名
            student_info: 学生情報（オプション）
            sharepoint_name: SharePoint上の名前（学生情報がない場合）
        
        Returns:
            作成されたフォルダのパス
        """
        safe_assignment_name = sanitize_filename(assignment_name)
        assignment_folder = os.path.join(base_folder, class_name, safe_assignment_name)
        
        if student_info:
            # 学生情報がある場合: クラス記号/出席番号_氏名
            class_folder = os.path.join(assignment_folder, student_info.class_code)
            student_folder = os.path.join(class_folder, student_info.folder_name)
        else:
            # 学生情報がない場合: SharePoint上の名前
            student_folder = os.path.join(assignment_folder, sharepoint_name)
        
        os.makedirs(student_folder, exist_ok=True)
        return student_folder
