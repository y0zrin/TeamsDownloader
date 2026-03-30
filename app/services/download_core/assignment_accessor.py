#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題アクセス共通処理

SharePoint接続、学生リスト取得など、
ダウンロードと未提出確認で共通する処理を提供
"""

import os
from typing import List, Tuple, Optional
from models.student import SharePointStudent
from services.download_core.progress_tracker import ProgressTracker
from utils.file_utils import sanitize_filename


class AssignmentAccessor:
    """課題アクセス共通クラス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
    
    def connect_to_sharepoint(
        self,
        class_config: dict,
        progress: ProgressTracker
    ) -> Tuple[str, str, str, str]:
        """SharePointに接続してドライブ情報を取得

        Returns:
            (site_id, drive_id, drive_name, base_folder)
        """
        # サイトIDとドライブIDを取得
        site_id, error_msg = self.api_client.get_site_id(class_config["site_path"])
        if not site_id:
            raise Exception(f"サイトにアクセスできません: {error_msg}")

        drive_id, drive_name = self.api_client.get_drive_id(site_id)
        if not drive_id:
            raise Exception("ドライブIDの取得に失敗")

        progress.log_success("SharePointに接続しました")

        # ベースフォルダを設定
        if drive_name == "Student Work":
            base_folder = "Working files"
        else:
            base_folder = "Student Work/Working files"

        progress.log_info(f"📂 フォルダパス: {drive_name}/{base_folder}")

        return site_id, drive_id, drive_name, base_folder
    
    def get_sharepoint_students(
        self,
        class_name: str,
        drive_id: str,
        base_folder: str,
        progress: ProgressTracker
    ) -> List[SharePointStudent]:
        """SharePoint上の学生リストを取得（名前履歴対応）
        
        Returns:
            SharePointStudentのリスト
        """
        progress.log_section("🔍 学生リストを取得中...")
        
        # 旧キャッシュを取得
        old_cached_list, _ = self.cache.get_students_list(class_name)
        
        # SharePointから最新リストを取得
        student_folders = self.api_client.get_student_folders(drive_id, base_folder)
        progress.log_info(f"✅ {len(student_folders)}人の学生フォルダを検出")
        
        # IDをキーにした辞書を作成（名前履歴を保持）
        student_id_map = {}
        
        # 旧キャッシュから履歴を構築
        if old_cached_list:
            for old_student in old_cached_list:
                student_id = old_student['id']
                student_id_map[student_id] = {
                    'id': student_id,
                    'current_name': old_student['name'],
                    'past_names': [old_student['name']]
                }
        
        # 最新リストで更新
        for student_folder in student_folders:
            student_id = student_folder['id']
            current_name = student_folder['name']
            
            if student_id in student_id_map:
                # 既存IDの場合
                old_name = student_id_map[student_id]['current_name']
                if current_name != old_name:
                    # 名前が変わった
                    progress.log_info(
                        f"🔄 名前変更検出: {old_name} → {current_name} "
                        f"(ID: {student_id[:8]}...)"
                    )
                    student_id_map[student_id]['current_name'] = current_name
                    # 重複を避けて履歴に追加
                    if current_name not in student_id_map[student_id]['past_names']:
                        student_id_map[student_id]['past_names'].append(current_name)
            else:
                student_id_map[student_id] = {
                    'id': student_id,
                    'current_name': current_name,
                    'past_names': [current_name]
                }
        
        # SharePointStudentオブジェクトのリストを作成
        sharepoint_students = []
        for student_id, data in student_id_map.items():
            for name in data['past_names']:
                sharepoint_students.append(SharePointStudent(
                    folder_id=student_id,
                    folder_name=name,
                    current_name=data['current_name']
                ))
        
        # キャッシュを更新
        simple_cache_list = [
            {'name': data['current_name'], 'id': student_id}
            for student_id, data in student_id_map.items()
        ]
        self.cache.set_students_list(class_name, simple_cache_list)
        
        progress.log_info(f"💾 統合学生リスト: {len(student_id_map)}人")
        
        return sharepoint_students
    
    def prepare_output_folder(
        self,
        output_base_dir: str,
        class_name: str,
        assignment_name: str
    ) -> str:
        """出力フォルダを準備
        
        Returns:
            出力フォルダのパス
        """
        safe_assignment_name = sanitize_filename(assignment_name)
        output_folder = os.path.join(output_base_dir, class_name, safe_assignment_name)
        os.makedirs(output_folder, exist_ok=True)
        return output_folder
