#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題ダウンロードサービス（リファクタリング版）

既存のインターフェースを維持しながら、内部実装を新しいアーキテクチャに置き換え
"""

from typing import Optional, Callable, List, Tuple
from services.download_core.coordinator import DownloadCoordinator
from models.download_result import UnsubmittedCheckResult, UnsubmittedStudent
from models.student import Student


class DownloadService:
    """課題ダウンロードを管理するサービス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.coordinator = DownloadCoordinator(api_client, cache_manager)
    
    def cancel(self):
        """ダウンロードをキャンセル"""
        self.coordinator.cancel()
    
    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.coordinator.reset_cancel()
    
    @property
    def cancelled(self) -> bool:
        """キャンセル状態を取得"""
        return self.coordinator.progress.check_cancelled()
    
    def get_unsubmitted_students(
        self,
        class_config: dict,
        assignment_name: str,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[List[dict], Optional[str]]:
        """未提出者を取得
        
        既存インターフェース用のラッパーメソッド
        
        Returns:
            (未提出者リスト, エラーメッセージ)
        """
        from services.download_core.progress_tracker import ProgressTracker
        
        progress = ProgressTracker(progress_callback)
        progress.log_header(f"📊 未提出者確認: {assignment_name}")
        
        class_name = class_config['name']
        
        # 学生情報を取得
        students_info = self.cache.get_students_info()
        if not students_info:
            return [], "❌ 学生情報が見つかりません(students.csv/xlsxを配置してください)"
        
        try:
            # サイトIDとドライブIDを取得
            site_id = self.api_client.get_site_id(class_config["site_path"])
            if not site_id:
                return [], "❌ サイトIDの取得に失敗"
            
            drive_id, drive_name = self.api_client.get_drive_id(site_id)
            if not drive_id:
                return [], "❌ ドライブIDの取得に失敗"
            
            # ベースフォルダを設定
            if drive_name == "Student Work":
                base_folder = "Working files"
            else:
                base_folder = "Student Work/Working files"
            
            # 学生リストを取得
            cached_students_list, _ = self.cache.get_students_list(class_name)
            
            if not cached_students_list:
                progress.log("🔍 学生フォルダをスキャン中...")
                cached_students_list = []
                student_folders = self.api_client.get_student_folders(drive_id, base_folder)
                for student_folder in student_folders:
                    cached_students_list.append({
                        'name': student_folder['name'],
                        'id': student_folder['id']
                    })
            
            # クラス内の学生情報を照合
            from utils.file_utils import clean_student_name
            current_class_students = {}
            
            progress.log("\n🔍 クラス内の学生情報を照合中...")
            
            for student in cached_students_list:
                student_name = student['name']
                cleaned_name = clean_student_name(student_name)
                name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
                
                if name_key not in students_info:
                    continue
                
                matched = students_info[name_key]
                
                if isinstance(matched, list):
                    # 複数クラス記号を持つ学生
                    cached_selection = self.cache.get_class_code_selection(class_name, student_name)
                    
                    if cached_selection:
                        student_info = next(
                            (s for s in matched if s['class_code'] == cached_selection),
                            None
                        )
                        if student_info:
                            current_class_students[name_key] = student_info
                            progress.log(f"   ✓ {student_name}: {cached_selection} (選択履歴)")
                    else:
                        current_class_students[name_key] = matched[0]
                        progress.log(f"   ✓ {student_name}: {matched[0]['class_code']} (デフォルト)")
                else:
                    current_class_students[name_key] = matched
                    progress.log(f"   ✓ {student_name}: {matched['class_code']}")
            
            progress.log(f"📋 対象学生数: {len(current_class_students)}人")
            
            if len(current_class_students) == 0:
                return [], "該当する学生が名簿に見つかりません"
            
            # 提出者を検出
            progress.log("\n🔍 提出状況確認中...")
            progress.log("   進捗状況を10人ごとに表示します\n")
            
            submitted_students = set()
            checked_count = 0
            
            for student in cached_students_list:
                if progress.check_cancelled():
                    return [], "キャンセルされました"
                
                student_name = student['name']
                cleaned_name = clean_student_name(student_name)
                name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
                
                if name_key not in current_class_students:
                    continue
                
                checked_count += 1
                student_path = f"{base_folder}/{student_name}"
                
                if checked_count % 10 == 0 or checked_count == len(current_class_students):
                    progress.log(f"   📊 進捗: {checked_count}/{len(current_class_students)}人確認完了")
                
                assignment_folders = self.api_client.get_assignment_folders(drive_id, student_path)
                
                for assignment_folder in assignment_folders:
                    folder_name = assignment_folder["name"]
                    search_name = assignment_name.replace('/', '_')
                    
                    if search_name.lower() in folder_name.lower():
                        submitted_students.add(name_key)
                        break
            
            progress.log(f"✅ {len(submitted_students)}人が提出済み")
            
            # 未提出者を抽出
            unsubmitted = []
            for name_key, student_info in current_class_students.items():
                if name_key not in submitted_students:
                    unsubmitted.append(student_info)
            
            # ソート
            unsubmitted.sort(key=lambda x: (
                x.get('class_code', ''),
                int(x.get('attendance_number', 0)) if x.get('attendance_number', '').isdigit() else 999
            ))
            
            progress.log(f"📋 未提出者: {len(unsubmitted)}人")
            
            if unsubmitted:
                progress.log("\n未提出者詳細:")
                for student in unsubmitted:
                    progress.log(
                        f"   - {student.get('student_name')} "
                        f"(クラスコード: {student.get('class_code')}, "
                        f"出席番号: {student.get('attendance_number')})"
                    )
            
            return unsubmitted, None
            
        except Exception as e:
            return [], f"エラー: {str(e)}"
    
    def download_assignment(
        self,
        class_config: dict,
        assignment_name: str,
        output_base_dir: str,
        progress_callback: Optional[Callable[[str], None]] = None,
        class_code_dialog_callback: Optional[Callable] = None,
        selected_students: Optional[List[str]] = None,
        name_mapping_dialog_callback: Optional[Callable] = None
    ) -> Tuple[int, int]:
        """課題をダウンロード
        
        既存インターフェース用のラッパーメソッド
        
        Returns:
            (成功数, 学生数)
        """
        result = self.coordinator.download_assignment(
            class_config,
            assignment_name,
            output_base_dir,
            progress_callback,
            class_code_dialog_callback,
            selected_students,
            name_mapping_dialog_callback
        )
        
        return result.file_count, result.student_count
