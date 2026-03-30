#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
名簿更新サービス

SharePoint上の名簿ファイルを取得し、ローカルに配置する。
パス: /sites/old-hal-oh-staff/Shared Documents/
      A001教務/F0301教務業務/M_名簿/{year}/{semester}/04_全クラス/
"""

import os
from datetime import datetime
from typing import Optional, Callable, Tuple, List

# SharePoint設定
ROSTER_SITE_PATH = "/sites/old-hal-oh-staff"
ROSTER_BASE_PATH = "A001教務/F0301教務業務/M_名簿"
ROSTER_FOLDER = "04_全クラス"

# 学期定義
SEMESTER_FIRST = "1_前期"   # 4月〜9月
SEMESTER_SECOND = "2_後期"  # 10月〜3月


def get_academic_year_semester(now=None):
    """現在の日付から年度・学期を判定

    日本の学校年度:
      前期: 4月〜9月 → {year}/1_前期
      後期: 10月〜3月 → {year-1}/2_後期（3月は前年度後期）

    Returns:
        (year, semester_folder): 例 (2025, "1_前期")
    """
    if now is None:
        now = datetime.now()

    month = now.month

    if month >= 4 and month <= 9:
        # 前期: 4月〜9月
        return now.year, SEMESTER_FIRST
    elif month >= 10:
        # 後期: 10月〜12月
        return now.year, SEMESTER_SECOND
    else:
        # 後期: 1月〜3月（前年度の後期）
        return now.year - 1, SEMESTER_SECOND


class RosterUpdater:
    """名簿更新サービス"""

    def __init__(self, api_client):
        self.api_client = api_client

    def update_roster(
        self,
        year: Optional[int] = None,
        semester: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str]:
        """名簿を更新

        Args:
            year: 年度（省略時は自動判定）
            semester: 学期フォルダ名（省略時は自動判定）
            progress_callback: 進捗コールバック

        Returns:
            (success, message)
        """
        log = progress_callback or print

        # 年度・学期の判定
        if year is None or semester is None:
            auto_year, auto_semester = get_academic_year_semester()
            year = year or auto_year
            semester = semester or auto_semester

        log(f"\n{'=' * 50}")
        log(f"📋 名簿更新: {year}年度 {'前期' if '前期' in semester else '後期'}")
        log(f"{'=' * 50}")

        try:
            # SharePointサイトに接続
            log("🔗 SharePointに接続中...")
            site_id, error = self.api_client.get_site_id(ROSTER_SITE_PATH)
            if not site_id:
                return False, f"サイトに接続できません: {error}"
            log("✅ 接続成功")

            # ドライブIDを取得
            drive_id, drive_name = self.api_client.get_drive_id(site_id)
            if not drive_id:
                return False, "ドライブが見つかりません"

            # 名簿フォルダのパスを構築
            roster_path = f"{ROSTER_BASE_PATH}/{year}/{semester}/{ROSTER_FOLDER}"
            log(f"📂 名簿パス: {roster_path}")

            # フォルダ内のファイル一覧を取得
            log("🔍 ファイルを検索中...")
            items = self.api_client.list_folder_items(drive_id, roster_path)

            if not items:
                # フォルダが見つからない場合、候補を探す
                return self._try_find_roster(drive_id, year, semester, log)

            # 名簿ファイルを特定（xlsx/csv）
            roster_files = [
                f for f in items
                if f.get("file") and (
                    f["name"].endswith(".xlsx")
                    or f["name"].endswith(".csv")
                )
            ]

            if not roster_files:
                log("⚠️ 名簿ファイル (.xlsx/.csv) が見つかりません")
                log("   フォルダ内のファイル:")
                for item in items:
                    log(f"     {item['name']}")
                return False, "名簿ファイルが見つかりません"

            # ファイルが複数ある場合は一覧表示
            if len(roster_files) > 1:
                log(f"📄 {len(roster_files)}個の名簿ファイルが見つかりました:")
                for i, f in enumerate(roster_files):
                    size = f.get("size", 0)
                    log(f"   {i + 1}. {f['name']} ({size:,} bytes)")

            # 最も大きいファイルを選択（通常は全クラス名簿が最大）
            target_file = max(roster_files, key=lambda f: f.get("size", 0))
            log(f"📥 ダウンロード: {target_file['name']}")

            # ダウンロード先を決定
            ext = os.path.splitext(target_file["name"])[1]
            save_name = f"students{ext}"
            save_path = os.path.abspath(save_name)

            # ダウンロード
            file_path = f"{roster_path}/{target_file['name']}"
            success = self.api_client.download_file(drive_id, file_path, save_path)

            if success:
                log(f"✅ 保存完了: {save_path}")

                # 暗号化キャッシュを削除（再生成させる）
                encrypted_cache = "students_encrypted.dat"
                if os.path.exists(encrypted_cache):
                    os.remove(encrypted_cache)
                    log("🔄 暗号化キャッシュをクリアしました（次回起動時に再生成）")

                return True, f"名簿を更新しました: {save_name}"
            else:
                return False, "ファイルのダウンロードに失敗しました"

        except Exception as e:
            log(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)

    def _try_find_roster(self, drive_id, year, semester, log):
        """名簿フォルダが見つからない場合に候補を探す"""
        log(f"⚠️ {year}/{semester}/{ROSTER_FOLDER} が見つかりません")
        log("🔍 利用可能なフォルダを検索中...")

        # 年度フォルダの一覧を取得
        year_path = f"{ROSTER_BASE_PATH}"
        year_items = self.api_client.list_folder_items(drive_id, year_path)

        if year_items:
            year_folders = [f["name"] for f in year_items if f.get("folder")]
            log(f"   利用可能な年度: {', '.join(sorted(year_folders))}")

            # 指定年度のフォルダ内を確認
            target_year_path = f"{ROSTER_BASE_PATH}/{year}"
            semester_items = self.api_client.list_folder_items(drive_id, target_year_path)

            if semester_items:
                sem_folders = [f["name"] for f in semester_items if f.get("folder")]
                log(f"   {year}年度のフォルダ: {', '.join(sorted(sem_folders))}")
            else:
                log(f"   {year}年度のフォルダはまだ存在しません")

        return False, f"{year}/{semester}/{ROSTER_FOLDER} が見つかりません"

    def list_available_rosters(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[dict]:
        """利用可能な名簿一覧を取得

        Returns:
            [{"year": int, "semester": str, "path": str}, ...]
        """
        log = progress_callback or print
        results = []

        try:
            site_id, error = self.api_client.get_site_id(ROSTER_SITE_PATH)
            if not site_id:
                log(f"❌ サイト接続失敗: {error}")
                return results

            drive_id, _ = self.api_client.get_drive_id(site_id)
            if not drive_id:
                return results

            # 年度フォルダ一覧
            year_items = self.api_client.list_folder_items(drive_id, ROSTER_BASE_PATH)
            year_folders = sorted(
                [f["name"] for f in year_items if f.get("folder")],
                reverse=True,
            )

            for year_name in year_folders[:3]:  # 直近3年分
                year_path = f"{ROSTER_BASE_PATH}/{year_name}"
                sem_items = self.api_client.list_folder_items(drive_id, year_path)

                for sem in sem_items:
                    if sem.get("folder"):
                        roster_path = f"{year_path}/{sem['name']}/{ROSTER_FOLDER}"
                        files = self.api_client.list_folder_items(drive_id, roster_path)
                        roster_files = [
                            f for f in files
                            if f.get("file") and (
                                f["name"].endswith(".xlsx")
                                or f["name"].endswith(".csv")
                            )
                        ]
                        if roster_files:
                            results.append({
                                "year": year_name,
                                "semester": sem["name"],
                                "files": [f["name"] for f in roster_files],
                                "path": roster_path,
                            })

        except Exception as e:
            log(f"❌ エラー: {e}")

        return results
