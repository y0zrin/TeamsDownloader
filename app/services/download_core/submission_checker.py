#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
未提出者確認サービス（リファクタリング版）

課題の提出状況を確認し、未提出者リストを返す
"""

from typing import List, Tuple, Optional, Callable
from services.download_core.assignment_accessor import AssignmentAccessor
from services.download_core.student_matcher import StudentMatcher
from services.download_core.progress_tracker import ProgressTracker
from models.student import sort_students
from utils.student_selector import select_class_code_for_student


class SubmissionChecker:
    """未提出者確認クラス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.accessor = AssignmentAccessor(api_client, cache_manager)
    
    def check_unsubmitted(
        self,
        class_config: dict,
        assignment_name: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[List[dict], Optional[str]]:
        """未提出者を確認
        
        Args:
            class_config: クラス設定
            assignment_name: 課題名
            progress_callback: 進捗コールバック
        
        Returns:
            (未提出者リスト, エラーメッセージ)
        """
        progress = ProgressTracker(progress_callback)
        progress.log_header(f"📊 未提出者確認: {assignment_name}")
        
        class_name = class_config['name']
        
        # 学生情報を取得
        students_info = self.cache.get_students_info()
        if not students_info:
            return [], "❌ 学生情報が見つかりません(students.csv/xlsxを配置してください)"
        
        try:
            # SharePointに接続
            _site_id, drive_id, drive_name, base_folder = self.accessor.connect_to_sharepoint(
                class_config, progress
            )
            
            # SharePoint上の学生リストを取得
            sharepoint_students = self.accessor.get_sharepoint_students(
                class_name, drive_id, base_folder, progress
            )
            
            # 学生情報を照合
            progress.log_section("🔍 クラス内の学生情報を照合中...")
            current_class_students = self._match_students(
                sharepoint_students, students_info, class_name, progress
            )
            
            if len(current_class_students) == 0:
                return [], "該当する学生が名簿に見つかりません"
            
            # 提出者を検出
            progress.log("\n🔍 提出状況確認中...")
            progress.log("   進捗状況を10人ごとに表示します\n")
            
            submitted_students = self._detect_submitted_students(
                sharepoint_students,
                current_class_students,
                drive_id,
                base_folder,
                assignment_name,
                progress
            )
            
            progress.log(f"✅ {len(submitted_students)}人が提出済み")
            
            # 未提出者を抽出
            unsubmitted = self._extract_unsubmitted(
                current_class_students,
                submitted_students,
                progress
            )
            
            return unsubmitted, None
            
        except Exception as e:
            return [], f"エラー: {str(e)}"
    
    def _match_students(
        self,
        sharepoint_students: List,
        students_info: dict,
        class_name: str,
        progress: ProgressTracker
    ) -> dict:
        """SharePoint上の学生を名簿と照合（共通関数を使用）"""
        current_class_students = {}
        
        # SharePoint上の学生名からユニークなキーを生成
        sp_names = {sp.name_key: sp.folder_name for sp in sharepoint_students}
        
        for name_key, student_name in sp_names.items():
            if name_key not in students_info:
                continue
            
            matched = students_info[name_key]
            
            if isinstance(matched, list):
                # 複数クラス記号を持つ学生の場合（共通関数を使用）
                cached_selection = self.cache.get_class_code_selection(
                    class_name, student_name
                )
                
                selected_info = select_class_code_for_student(
                    matched, class_name, cached_selection
                )
                
                current_class_students[name_key] = selected_info
                
                if cached_selection:
                    progress.log(
                        f"   ✓ {student_name}: {selected_info['class_code']} (選択履歴)"
                    )
                else:
                    progress.log(
                        f"   ✓ {student_name}: {selected_info['class_code']} (自動選択)"
                    )
            else:
                current_class_students[name_key] = matched
                progress.log(f"   ✓ {student_name}: {matched['class_code']}")
        
        progress.log(f"📋 対象学生数: {len(current_class_students)}人")
        return current_class_students
    
    def _detect_submitted_students(
        self,
        sharepoint_students: List,
        current_class_students: dict,
        drive_id: str,
        base_folder: str,
        assignment_name: str,
        progress: ProgressTracker
    ) -> set:
        """提出済み学生を検出"""
        submitted_students = set()
        checked_count = 0
        
        # SharePointStudentからname_keyとfolder_nameの対応を作成
        sp_name_map = {sp.name_key: sp.folder_name for sp in sharepoint_students}
        
        for name_key in current_class_students.keys():
            if progress.check_cancelled():
                break
            
            if name_key not in sp_name_map:
                continue
            
            checked_count += 1
            student_name = sp_name_map[name_key]
            student_path = f"{base_folder}/{student_name}"
            
            if checked_count % 10 == 0 or checked_count == len(current_class_students):
                progress.log(
                    f"   📊 進捗: {checked_count}/{len(current_class_students)}人確認完了"
                )
            
            # 課題フォルダを検索
            assignment_folders = self.api_client.get_assignment_folders(
                drive_id, student_path
            )
            
            search_name = assignment_name.replace('/', '_')
            for folder in assignment_folders:
                if search_name.lower() in folder["name"].lower():
                    submitted_students.add(name_key)
                    break
        
        return submitted_students
    
    def _extract_unsubmitted(
        self,
        current_class_students: dict,
        submitted_students: set,
        progress: ProgressTracker
    ) -> List[dict]:
        """未提出者を抽出してソート（共通関数を使用）"""
        unsubmitted = []
        for name_key, student_info in current_class_students.items():
            if name_key not in submitted_students:
                unsubmitted.append(student_info)
        
        # 共通関数を使用してソート
        unsubmitted = sort_students(unsubmitted)
        
        progress.log(f"📋 未提出者: {len(unsubmitted)}人")
        
        if unsubmitted:
            progress.log("\n未提出者詳細:")
            for student in unsubmitted:
                progress.log(
                    f"   - {student.get('student_name')} "
                    f"(クラスコード: {student.get('class_code')}, "
                    f"出席番号: {student.get('attendance_number')})"
                )
        
        return unsubmitted
