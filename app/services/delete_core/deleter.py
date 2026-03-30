#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題削除オーケストレーション

SharePoint上の課題フォルダ（学生ごと）を削除する。
ローカルファイルには一切触れない。
"""

import time
from typing import Optional, Callable, List

from models.delete_result import DeleteResult, StudentDeleteResult
from services.download_core.assignment_accessor import AssignmentAccessor
from services.download_core.progress_tracker import ProgressTracker
from utils.exceptions import DeleteCancelledError


class AssignmentDeleter:
    """課題削除オーケストレーションクラス"""

    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.progress = ProgressTracker()
        self.accessor = AssignmentAccessor(api_client, cache_manager)

    def delete_assignment(
        self,
        class_config: dict,
        assignment_name: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> DeleteResult:
        """課題をSharePointから削除する

        各学生フォルダ配下の該当課題フォルダを削除する。
        学生フォルダ自体は削除しない。

        Args:
            class_config: クラス設定 (name, site_path等)
            assignment_name: 削除する課題名
            progress_callback: 進捗コールバック

        Returns:
            DeleteResult: 削除結果
        """
        self.progress = ProgressTracker(progress_callback)
        self.progress.reset_cancel()

        result = DeleteResult(assignment_name=assignment_name)

        self.progress.log_header(f"🗑️ 課題削除開始: {assignment_name}")

        try:
            # SharePointに接続
            site_id, drive_id, drive_name, base_folder = self.accessor.connect_to_sharepoint(
                class_config, self.progress
            )

            # 学生フォルダ一覧を取得
            self.progress.log_section("🔍 学生フォルダを取得中...")
            student_folders = self.api_client.get_student_folders(drive_id, base_folder)
            self.progress.log_info(f"✅ {len(student_folders)}人の学生フォルダを検出")

            result.total_students = len(student_folders)

            # 課題名のマッチング用
            search_name = assignment_name.replace('/', '_').lower()

            # 各学生フォルダから課題フォルダを探して削除
            self.progress.log_section("🗑️ 削除処理中...")
            self.progress.log_info("   進捗状況を5人ごとに表示します\n")

            deleted_count = 0
            processed_count = 0

            for student_folder in student_folders:
                if self.progress.check_cancelled():
                    result.cancelled = True
                    raise DeleteCancelledError()

                processed_count += 1
                student_name = student_folder["name"]

                # 進捗ログ
                if processed_count % 5 == 0 or processed_count == 1:
                    self.progress.log_progress(
                        processed_count, len(student_folders),
                        f"処理中: {student_name}"
                    )

                # 学生フォルダ内の課題フォルダを検索
                student_path = f"{base_folder}/{student_name}"
                assignment_folders = self.api_client.get_assignment_folders(
                    drive_id, student_path
                )

                # 課題名でマッチ
                target_folder = None
                for folder in assignment_folders:
                    if search_name in folder["name"].lower():
                        target_folder = folder
                        break

                if not target_folder:
                    result.skip_count += 1
                    continue

                # 削除実行
                success, error = self.api_client.delete_item(
                    drive_id, target_folder["id"]
                )

                result.add_result(StudentDeleteResult(
                    student_name=student_name,
                    success=success,
                    error=error,
                ))

                if success:
                    deleted_count += 1
                else:
                    self.progress.log_error(
                        f"  ❌ {student_name}: {error}"
                    )

                # レート制限対策
                time.sleep(0.25)

            # キャッシュ無効化
            self.progress.log_section("💾 キャッシュを更新中...")
            self._invalidate_cache(class_config["name"])

            # 結果ログ
            self._log_result(result, deleted_count)

            # ごみ箱を空にする（設定がONの場合）
            if deleted_count > 0 and self.cache.get_empty_recycle_bin():
                self._empty_recycle_bin(site_id)

            return result

        except DeleteCancelledError:
            self.progress.log_warning("削除がキャンセルされました")
            result.cancelled = True
            return result

        except Exception as e:
            self.progress.log_error(f"削除エラー: {e}")
            import traceback
            traceback.print_exc()
            return result

    def _empty_recycle_bin(self, site_id: str):
        """サイトのごみ箱を空にする"""
        self.progress.log_section("🗑️ ごみ箱を空にしています...")

        items = self.api_client.get_recycle_bin_items(site_id)
        if not items:
            self.progress.log_info("ごみ箱は空です")
            return

        self.progress.log_info(f"ごみ箱のアイテム数: {len(items)}件")

        purged = 0
        failed = 0
        for item in items:
            if self.progress.check_cancelled():
                self.progress.log_warning("ごみ箱の削除がキャンセルされました")
                break

            success, error = self.api_client.purge_recycle_bin_item(
                site_id, item["id"]
            )
            if success:
                purged += 1
            else:
                failed += 1
                self.progress.log_error(f"  ❌ 完全削除失敗: {error}")

            time.sleep(0.25)

        self.progress.log_info(f"✅ ごみ箱から{purged}件を完全削除しました")
        if failed > 0:
            self.progress.log_error(f"   失敗: {failed}件")

    def _invalidate_cache(self, class_name: str):
        """課題キャッシュを無効化"""
        if class_name in self.cache.cache_data:
            del self.cache.cache_data[class_name]
            self.cache.save_cache()
            self.progress.log_info("✅ 課題キャッシュを更新しました")

    def _log_result(self, result: DeleteResult, deleted_count: int):
        """結果をログ出力"""
        self.progress.log("")
        if deleted_count == 0 and result.skip_count == result.total_students:
            self.progress.log_warning("該当する課題フォルダが見つかりませんでした")
        else:
            self.progress.log_success("削除完了!")
            self.progress.log_info(f"   対象学生数: {result.total_students}人")
            self.progress.log_info(f"   削除成功: {result.success_count}人")
            self.progress.log_info(f"   スキップ（課題なし）: {result.skip_count}人")
            if result.fail_count > 0:
                self.progress.log_error(f"   削除失敗: {result.fail_count}人")

    def cancel(self):
        """削除をキャンセル"""
        self.progress.cancel()

    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.progress.reset_cancel()
