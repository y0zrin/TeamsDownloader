#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファイル取得とダウンロード
"""

import os
from typing import List, Tuple
from models.student import Student
from models.download_result import DownloadedFile
from utils.file_utils import sanitize_filename


class FileFetcher:
    """ファイル取得クラス"""
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    def fetch_assignment_files(
        self,
        drive_id: str,
        student_folder_path: str,
        assignment_name: str
    ) -> Tuple[List[dict], str]:
        """学生の課題フォルダ内のファイルを取得
        
        Args:
            drive_id: ドライブID
            student_folder_path: 学生フォルダのパス
            assignment_name: 課題名
        
        Returns:
            (ファイルリスト, 課題フォルダパス)
        """
        # 学生フォルダ内の課題フォルダを検索
        assignment_folders = self.api_client.get_assignment_folders(drive_id, student_folder_path)
        
        # 課題名で絞り込み
        search_name = assignment_name.replace('/', '_')
        
        for folder in assignment_folders:
            folder_name = folder["name"]
            if search_name.lower() in folder_name.lower():
                assignment_path = f"{student_folder_path}/{folder_name}"
                files = self.api_client.get_files_in_folder(drive_id, assignment_path)
                return files, assignment_path
        
        return [], ""
    
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
        results = []
        
        for file_item in files:
            file_name = file_item["name"]
            file_path = f"{assignment_path}/{file_name}"
            save_path = os.path.join(output_folder, file_name)
            
            success = self.api_client.download_file(drive_id, file_path, save_path)
            
            results.append(DownloadedFile(
                file_name=file_name,
                file_path=save_path,
                success=success,
                error=None if success else "ダウンロード失敗"
            ))
        
        return results
    
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
