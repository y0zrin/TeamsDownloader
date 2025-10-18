#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダウンロード全体制御（リファクタリング版）

AssignmentAccessorを使用して共通処理を簡素化
"""

from typing import Optional, Callable, List
from models.student import SharePointStudent, Student
from models.download_result import DownloadResult, StudentDownloadResult
from services.download_core.assignment_accessor import AssignmentAccessor
from services.download_core.progress_tracker import ProgressTracker
from services.download_core.student_matcher import StudentMatcher
from services.download_core.file_fetcher import FileFetcher
from utils.exceptions import DownloadCancelledError


class DownloadCoordinator:
    """ダウンロード全体制御クラス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.progress = ProgressTracker()
        self.accessor = AssignmentAccessor(api_client, cache_manager)
        self.file_fetcher = FileFetcher(api_client)
    
    def download_assignment(
        self,
        class_config: dict,
        assignment_name: str,
        output_base_dir: str,
        progress_callback: Optional[Callable[[str], None]] = None,
        class_code_dialog_callback: Optional[Callable] = None,
        selected_students: Optional[List[str]] = None,
        name_mapping_dialog_callback: Optional[Callable] = None
    ) -> DownloadResult:
        """課題をダウンロード"""
        # 進捗トラッカーを初期化
        self.progress = ProgressTracker(progress_callback)
        self.progress.reset_cancel()
        
        # ヘッダー出力
        if selected_students:
            self.progress.log_header(
                f"📥 課題ダウンロード開始(特定学生のみ): {assignment_name}"
            )
        else:
            self.progress.log_header(f"📥 課題ダウンロード開始: {assignment_name}")
        
        try:
            # SharePointに接続
            drive_id, drive_name, base_folder = self.accessor.connect_to_sharepoint(
                class_config, self.progress
            )
            
            # 出力フォルダを準備
            output_folder = self.accessor.prepare_output_folder(
                output_base_dir, class_config['name'], assignment_name
            )
            self.progress.log_info(f"\n💾 保存先: {output_folder}")
            
            # 学生リストを取得
            sharepoint_students = self.accessor.get_sharepoint_students(
                class_config['name'], drive_id, base_folder, self.progress
            )
            
            # フィルタリング（特定学生指定時）
            if selected_students:
                sharepoint_students = self._filter_students(
                    sharepoint_students, selected_students
                )
                self.progress.log_info(
                    f"🎯 ダウンロード対象: {len(sharepoint_students)}人"
                )
            
            # StudentMatcherを初期化
            students_info = self.cache.get_students_info()
            student_matcher = (
                StudentMatcher(self.cache, students_info)
                if students_info else None
            )
            
            # ダウンロード実行
            result = self._execute_download(
                sharepoint_students,
                drive_id,
                base_folder,
                assignment_name,
                output_folder,
                class_config['name'],
                student_matcher,
                class_code_dialog_callback,
                name_mapping_dialog_callback
            )
            
            # 結果出力
            self._log_result(result)
            
            return result
            
        except DownloadCancelledError:
            self.progress.log_warning("ダウンロードがキャンセルされました")
            return DownloadResult(0, 0, output_base_dir, cancelled=True)
        
        except Exception as e:
            self.progress.log_error(f"ダウンロードエラー: {e}")
            import traceback
            traceback.print_exc()
            result = DownloadResult(0, 0, output_base_dir)
            result.add_error(str(e))
            return result
    
    def _filter_students(
        self,
        sharepoint_students: List[SharePointStudent],
        selected_students: List[dict]  # 型をdictのリストに変更
    ) -> List[SharePointStudent]:
        """特定学生でフィルタリング（class_code + attendance_numberで照合）"""
        if not selected_students:
            return sharepoint_students
        
        # 選択された学生のclass_code + attendance_numberのセットを作成
        selected_keys = set()
        for s in selected_students:
            key = (s.get('class_code'), str(s.get('attendance_number')))
            selected_keys.add(key)
        
        # StudentMatcherを使って各SharePoint学生を名簿と照合
        filtered = []
        students_info = self.cache.get_students_info()
        if not students_info:
            return sharepoint_students
        
        student_matcher = StudentMatcher(self.cache, students_info)
        
        for sp_student in sharepoint_students:
            # 学生情報を照合（IDマッピング考慮）
            student_info = student_matcher.match_student(
                sp_student, "", None, None
            )
            
            if student_info:
                key = (student_info.class_code, str(student_info.attendance_number))
                if key in selected_keys:
                    filtered.append(sp_student)
        
        return filtered
    
    def _execute_download(
        self,
        sharepoint_students: List[SharePointStudent],
        drive_id: str,
        base_folder: str,
        assignment_name: str,
        output_folder: str,
        class_name: str,
        student_matcher: Optional[StudentMatcher],
        class_code_dialog_callback: Optional[Callable],
        name_mapping_dialog_callback: Optional[Callable]
    ) -> DownloadResult:
        """ダウンロードを実行"""
        result = DownloadResult(0, 0, output_folder)
        
        # 課題提出者をスキャン
        self.progress.log_section("🔍 課題提出フォルダをスキャン中...")
        self.progress.log_info("   進捗状況を5人ごとに表示します\n")
        
        student_data_list = []
        scanned_count = 0
        
        for sp_student in sharepoint_students:
            if self.progress.check_cancelled():
                raise DownloadCancelledError()
            
            # 除外チェック
            if student_matcher and student_matcher.is_excluded(sp_student.folder_id):
                self.progress.log_info(
                    f"  ⏭️ {sp_student.folder_name}: 除外済み（スキップ）"
                )
                continue
            
            scanned_count += 1
            
            # 進捗ログ
            if scanned_count % 5 == 0 or scanned_count == 1:
                self.progress.log_progress(
                    scanned_count, len(sharepoint_students),
                    f"処理中: {sp_student.folder_name}"
                )
            
            # 課題フォルダをチェック
            student_path = f"{base_folder}/{sp_student.folder_name}"
            files, assignment_path = self.file_fetcher.fetch_assignment_files(
                drive_id, student_path, assignment_name
            )
            
            if files:
                # 学生情報を照合
                student_info = None
                if student_matcher:
                    student_info = student_matcher.match_student(
                        sp_student,
                        class_name,
                        class_code_dialog_callback,
                        name_mapping_dialog_callback
                    )
                
                student_data_list.append({
                    'sp_student': sp_student,
                    'student_info': student_info,
                    'files': files,
                    'assignment_path': assignment_path
                })
        
        if scanned_count > 0:
            self.progress.log_info(f"\n   ✅ スキャン完了: {scanned_count}人")
        
        result.student_count = len(student_data_list)
        
        # 学生一覧を表示
        self._log_student_list(student_data_list)
        
        # ダウンロード実行
        self.progress.log_section("📥 ダウンロード開始...")
        
        for student_data in student_data_list:
            if self.progress.check_cancelled():
                raise DownloadCancelledError()
            
            downloaded = self._download_student_files(
                student_data, drive_id, output_folder,
                class_name, assignment_name
            )
            result.add_student_result(downloaded)
            result.file_count += downloaded.file_count
        
        return result
    
    def _download_student_files(
        self,
        student_data: dict,
        drive_id: str,
        output_folder: str,
        class_name: str,
        assignment_name: str
    ) -> StudentDownloadResult:
        """学生のファイルをダウンロード"""
        sp_student = student_data['sp_student']
        student_info = student_data['student_info']
        files = student_data['files']
        assignment_path = student_data['assignment_path']
        
        # ログ出力
        if student_info:
            self.progress.log_info(f"  📁 {student_info} の提出物を処理中...")
        else:
            self.progress.log_info(
                f"  📁 {sp_student.folder_name} の提出物を処理中..."
            )
        
        # 出力フォルダを作成
        student_output = self.file_fetcher.create_output_folder(
            output_folder, class_name, assignment_name,
            student_info, sp_student.folder_name
        )
        
        # ファイルをダウンロード
        self.progress.log_info(f"     ファイル数: {len(files)}個")
        downloaded_files = self.file_fetcher.download_files(
            drive_id, assignment_path, files, student_output
        )
        
        return StudentDownloadResult(
            sharepoint_name=sp_student.folder_name,
            student_info=student_info,
            files=downloaded_files,
            folder_path=student_output
        )
    
    def _log_student_list(self, student_data_list: List[dict]):
        """学生一覧をログ出力"""
        self.progress.log_section(
            f"📋 検出された学生一覧 ({len(student_data_list)}人):"
        )
        self.progress.log("=" * 60)
        
        # 学生情報でソート
        with_info = [s for s in student_data_list if s['student_info']]
        without_info = [s for s in student_data_list if not s['student_info']]
        
        with_info.sort(key=lambda x: (
            x['student_info'].class_code,
            int(x['student_info'].attendance_number)
            if x['student_info'].attendance_number.isdigit()
            else 999
        ))
        without_info.sort(key=lambda x: x['sp_student'].folder_name)
        
        for idx, data in enumerate(with_info, 1):
            self.progress.log(f"   {idx:2d}. {data['student_info']}")
        
        if without_info:
            self.progress.log("\n   名簿外の学生:")
            for idx, data in enumerate(without_info, 1):
                self.progress.log(
                    f"   {idx:2d}. {data['sp_student'].folder_name}"
                )
        
        self.progress.log("=" * 60)
    
    def _log_result(self, result: DownloadResult):
        """結果をログ出力"""
        if result.student_count == 0:
            self.progress.log_warning("課題が見つかりませんでした")
        else:
            self.progress.log_success("ダウンロード完了!")
            self.progress.log_info(f"   学生数: {result.student_count}人")
            self.progress.log_info(f"   ファイル数: {result.file_count}個")
            self.progress.log_info(f"   保存先: {result.folder_path}")
    
    def cancel(self):
        """ダウンロードをキャンセル"""
        self.progress.cancel()
    
    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.progress.reset_cancel()
