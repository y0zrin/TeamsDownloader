#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダウンロード全体制御（リファクタリング版）

AssignmentAccessorを使用して共通処理を簡素化
"""

from typing import Optional, Callable, Dict, List, Tuple
from models.student import SharePointStudent, Student
from models.download_result import DownloadedFile, DownloadResult, StudentDownloadResult
from services.download_core.assignment_accessor import AssignmentAccessor
from services.download_core.progress_tracker import ProgressTracker
from services.download_core.student_matcher import StudentMatcher
from services.download_core.file_fetcher import FileFetcher, Submission
from utils.exceptions import DownloadCancelledError
from utils.parallel import imap_unordered

# 提出フォルダのスキャン並列数（1人あたり2回のAPI呼び出しを並列化）
SCAN_WORKERS = 6

# ファイル転送の並列数
DOWNLOAD_WORKERS = 4


class DownloadCoordinator:
    """ダウンロード全体制御クラス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.progress = ProgressTracker()
        self.accessor = AssignmentAccessor(api_client, cache_manager)
        self.file_fetcher = FileFetcher(api_client)
        # キャンセルを転送中にも効かせる
        self.file_fetcher.should_cancel = lambda: self.progress.check_cancelled()
    
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
            # 設定を反映（設定変更を即座に反映させるため毎回読み込む）
            exclude_patterns = self.cache.get_exclude_patterns()
            self.file_fetcher.exclude_patterns = exclude_patterns
            if exclude_patterns:
                self.progress.log_info(
                    f"🚫 除外パターン: {', '.join(exclude_patterns)}"
                )
            
            latest_only = self.cache.get_latest_only()
            self.file_fetcher.latest_only = latest_only
            self.progress.log_info(
                "🆕 最新の提出物のみダウンロード（拡張子ごとに最新の1件）"
                if latest_only else
                "📚 提出物をすべてダウンロード"
            )
            
            # SharePointに接続
            _site_id, drive_id, drive_name, base_folder = self.accessor.connect_to_sharepoint(
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
        
        # 除外済みの学生を先に取り除く（無駄なAPI呼び出しを減らす）
        targets = []
        for sp_student in sharepoint_students:
            if student_matcher and student_matcher.is_excluded(sp_student.folder_id):
                self.progress.log_info(
                    f"  ⏭️ {sp_student.folder_name}: 除外済み（スキップ）"
                )
                continue
            targets.append(sp_student)
        
        # 課題提出者をスキャン（並列）
        self.progress.log_section("🔍 課題提出フォルダをスキャン中...")
        self.progress.log_info(f"   {SCAN_WORKERS}並列で確認します\n")
        
        submissions = self._scan_submissions(
            targets, drive_id, base_folder, assignment_name
        )
        
        if targets:
            self.progress.log_info(f"\n   ✅ スキャン完了: {len(targets)}人")
        
        # 学生情報の照合（ダイアログを出す場合があるので直列・元の順序を維持）
        student_data_list = []
        for sp_student in targets:
            submission = submissions.get(sp_student.folder_id)
            if not submission:
                continue
            
            student_info = None
            if student_matcher:
                student_info = student_matcher.match_student(
                    sp_student,
                    class_name,
                    class_code_dialog_callback,
                    name_mapping_dialog_callback
                )
            
            self._log_older_submissions(sp_student, student_info, submission)
            
            student_data_list.append({
                'sp_student': sp_student,
                'student_info': student_info,
                'files': submission.files,
                'assignment_path': submission.path
            })
        
        result.student_count = len(student_data_list)
        
        # 学生一覧を表示
        self._log_student_list(student_data_list)
        
        # ダウンロード実行（並列）
        self.progress.log_section("📥 ダウンロード開始...")
        
        student_results = self._download_files(
            student_data_list, drive_id, output_folder, class_name, assignment_name
        )
        
        for student_result in student_results:
            result.add_student_result(student_result)
            result.file_count += student_result.file_count
            result.skipped_count += student_result.skipped_count
            result.reused_count += student_result.reused_count
        
        return result
    
    def _scan_submissions(
        self,
        sharepoint_students: List[SharePointStudent],
        drive_id: str,
        base_folder: str,
        assignment_name: str
    ) -> Dict[str, Submission]:
        """課題提出フォルダを並列にスキャン
        
        Returns:
            {folder_id: Submission} （提出のあった学生のみ）
        """
        submissions = {}
        total = len(sharepoint_students)
        
        if not total:
            return submissions
        
        scanned = 0
        
        def scan(sp_student):
            return self.file_fetcher.fetch_assignment_files(
                drive_id,
                f"{base_folder}/{sp_student.folder_name}",
                assignment_name
            )
        
        for sp_student, found, error in imap_unordered(
            sharepoint_students, scan, SCAN_WORKERS,
            should_cancel=self.progress.check_cancelled
        ):
            if self.progress.check_cancelled():
                raise DownloadCancelledError()
            
            if error:
                self.progress.log_warning(
                    f"{sp_student.folder_name}: 確認に失敗しました ({error})"
                )
                continue
            
            scanned += 1
            if scanned == 1 or scanned % 5 == 0 or scanned == total:
                self.progress.log_progress(
                    scanned, total, f"処理中: {sp_student.folder_name}"
                )
            
            if found.files:
                submissions[sp_student.folder_id] = found
        
        # 応答待ちの途中で打ち切られた場合
        if self.progress.check_cancelled():
            raise DownloadCancelledError()
        
        return submissions
    
    def _download_files(
        self,
        student_data_list: List[dict],
        drive_id: str,
        output_folder: str,
        class_name: str,
        assignment_name: str
    ) -> List[StudentDownloadResult]:
        """学生のファイルを並列にダウンロード"""
        if not student_data_list:
            return []
        
        # 出力フォルダを先に作り、ファイル単位のタスクに展開
        tasks = []
        for student_data in student_data_list:
            student_data['output'] = self.file_fetcher.create_output_folder(
                output_folder, class_name, assignment_name,
                student_data['student_info'], student_data['sp_student'].folder_name
            )
            student_data['results'] = []
            
            for file_item in student_data['files']:
                tasks.append((student_data, file_item))
        
        total = len(tasks)
        self.progress.log_info(
            f"{len(student_data_list)}人 / {total}ファイル "
            f"（{DOWNLOAD_WORKERS}並列）\n"
        )
        
        completed = 0
        
        def download(task):
            student_data, file_item = task
            return self.file_fetcher.download_file_item(
                drive_id,
                student_data['assignment_path'],
                file_item,
                student_data['output']
            )
        
        for task, downloaded, error in imap_unordered(
            tasks, download, DOWNLOAD_WORKERS,
            should_cancel=self.progress.check_cancelled
        ):
            if self.progress.check_cancelled():
                raise DownloadCancelledError()
            
            student_data, file_item = task
            
            if error:
                downloaded = DownloadedFile(
                    file_name=file_item.get("name", "?"),
                    file_path="",
                    success=False,
                    error=str(error)
                )
            
            student_data['results'].append(downloaded)
            completed += 1
            self._log_downloaded_file(completed, total, student_data, downloaded)
        
        # 応答待ちの途中で打ち切られた場合
        if self.progress.check_cancelled():
            raise DownloadCancelledError()
        
        return [
            StudentDownloadResult(
                sharepoint_name=student_data['sp_student'].folder_name,
                student_info=student_data['student_info'],
                files=student_data['results'],
                folder_path=student_data['output']
            )
            for student_data in student_data_list
        ]
    
    def _log_older_submissions(
        self,
        sp_student: SharePointStudent,
        student_info: Optional[Student],
        submission: Submission
    ):
        """最新版以外をスキップしたことをログ出力"""
        if not submission.old_files and not submission.other_folders:
            return
        
        name = str(student_info) if student_info else sp_student.folder_name
        
        for folder in submission.other_folders:
            self.progress.log_info(
                f"  🆕 [{name}] 古いフォルダをスキップ: {folder['name']}"
            )
        
        for old_file, newest in submission.old_files:
            self.progress.log_info(
                f"  🆕 [{name}] 旧版をスキップ: {old_file['name']} "
                f"→ {newest['name']}"
            )
    
    def _log_downloaded_file(
        self,
        completed: int,
        total: int,
        student_data: dict,
        downloaded: DownloadedFile
    ):
        """ファイル1個分の結果をログ出力"""
        student_info = student_data['student_info']
        name = str(student_info) if student_info else student_data['sp_student'].folder_name
        
        if downloaded.skipped:
            mark = f"⏭️ 除外({downloaded.skip_reason})"
        elif downloaded.reused:
            mark = "✔️ 取得済み"
        elif downloaded.success:
            mark = "✅"
        else:
            mark = "❌ 失敗"
        
        self.progress.log_info(
            f"({completed}/{total}) {mark} [{name}] {downloaded.file_name}"
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
            if result.reused_count:
                self.progress.log_info(
                    f"   取得済みのためスキップ: {result.reused_count}個"
                )
            if result.skipped_count:
                self.progress.log_info(
                    f"   除外したファイル: {result.skipped_count}個"
                )
            self.progress.log_info(f"   保存先: {result.folder_path}")
    
    def cancel(self):
        """ダウンロードをキャンセル"""
        self.progress.cancel()
    
    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.progress.reset_cancel()
