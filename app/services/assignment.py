#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題管理サービス
"""

import json
import os


class AssignmentService:
    """課題とクラスの管理サービス"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"classes": []}
    
    def save_config(self):
        """設定ファイルに保存(古い形式を自動変換)"""
        # 全クラスを新しい形式に変換
        for i, cls in enumerate(self.config["classes"]):
            self.config["classes"][i] = self.migrate_old_config(cls)
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def migrate_old_config(self, cls):
        """古い設定ファイル形式を新しい形式に変換"""
        if "site_path" not in cls and "name" in cls:
            cls["site_path"] = f"/sites/{cls['name']}"
        return cls
    
    def add_class(self, class_name):
        """クラスを追加"""
        # SharePoint Graph API用に/を-に置換
        original_name = class_name
        sanitized_name = class_name.replace('/', '-')
        
        # 既に登録済みかチェック
        for cls in self.config["classes"]:
            if cls["name"] == sanitized_name:
                return False, f"{sanitized_name} は既に登録されています"
        
        # SharePointサイトURLを構築
        site_url = f"https://nkzacjp.sharepoint.com/sites/{sanitized_name}"
        
        self.config["classes"].append({
            "name": sanitized_name,
            "site_url": site_url,
            "site_path": f"/sites/{sanitized_name}"
        })
        
        self.save_config()
        
        # 置換があった場合は通知
        if original_name != sanitized_name:
            return True, f"✅ {original_name} を {sanitized_name} として追加しました\n   (SharePoint API対応のため / を - に置換)"
        else:
            return True, f"✅ {sanitized_name} を追加しました"
    
    def edit_class(self, index, new_class_name):
        """クラスを編集(新機能)"""
        if not (0 <= index < len(self.config["classes"])):
            return False, "❌ 無効な番号です"
        
        # 同じ名前がすでに存在するかチェック(自分以外)
        for i, cls in enumerate(self.config["classes"]):
            if i != index and cls["name"] == new_class_name:
                return False, f"{new_class_name} は既に登録されています"
        
        old_name = self.config["classes"][index]["name"]
        
        # SharePointサイトURLを更新
        site_url = f"https://nkzacjp.sharepoint.com/sites/{new_class_name}"
        
        self.config["classes"][index] = {
            "name": new_class_name,
            "site_url": site_url,
            "site_path": f"/sites/{new_class_name}"
        }
        
        self.save_config()
        return True, f"✅ {old_name} を {new_class_name} に変更しました"
    
    def delete_class(self, index):
        """クラスを削除"""
        if 0 <= index < len(self.config["classes"]):
            deleted = self.config["classes"].pop(index)
            self.save_config()
            return True, f"✅ {deleted['name']} を削除しました"
        return False, "❌ 無効な番号です"
    
    def get_classes(self):
        """登録済みクラス一覧を取得"""
        return self.config["classes"]
    
    def get_class(self, index):
        """特定のクラスを取得"""
        if 0 <= index < len(self.config["classes"]):
            return self.config["classes"][index]
        return None
    
    def scan_assignments(self, api_client, class_config, cache_manager, progress_callback=None):
        """課題一覧をスキャン（クラス記号も収集）- リファクタリング版"""
        def log(msg):
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)
        
        class_config = self.migrate_old_config(class_config)
        
        # サイトIDを取得
        site_id = api_client.get_site_id(class_config["site_path"])
        if not site_id:
            log("❌ サイトIDの取得に失敗")
            return []
        
        # ドライブIDを取得
        drive_id, drive_name = api_client.get_drive_id(site_id)
        if not drive_id:
            log("❌ ドライブIDの取得に失敗")
            return []
        
        log("✅ SharePointに接続しました")
        
        # ベースフォルダを設定
        if drive_name == "Student Work":
            base_folder = "Working files"
        else:
            base_folder = "Student Work/Working files"
        
        log(f"📂 フォルダパス: {drive_name}/{base_folder}")
        
        # 学生フォルダを取得
        student_folders = api_client.get_student_folders(drive_id, base_folder)
        total_students = len(student_folders)
        
        log(f"👥 全{total_students}人の学生フォルダを検出")
        
        # 学生リストを作成してキャッシュ
        students_list = []
        for student_folder in student_folders:
            students_list.append({
                'name': student_folder['name'],
                'id': student_folder['id']
            })
        
        # 学生リストをキャッシュに保存
        cache_manager.set_students_list(class_config['name'], students_list)
        log(f"💾 {total_students}人の学生リストをキャッシュに保存")
        
        # クラス記号を収集（共通関数を使用）
        from utils.file_utils import clean_student_name
        from utils.student_selector import get_class_codes_from_students
        
        students_info = cache_manager.get_students_info()
        collected_class_codes = set()
        
        if students_info:
            log(f"\n🔍 クラス記号を収集中...")
            for student_folder in student_folders:
                student_name = student_folder['name']
                cleaned_name = clean_student_name(student_name)
                name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
                
                if name_key in students_info:
                    info = students_info[name_key]
                    if isinstance(info, list):
                        # 複数クラス記号を持つ学生の場合（共通関数を使用）
                        cached_selection = cache_manager.get_class_code_selection(
                            class_config['name'], student_name
                        )
                        
                        selected_code = get_class_codes_from_students(
                            info, class_config['name'], cached_selection
                        )
                        
                        if selected_code:
                            collected_class_codes.add(selected_code)
                    else:
                        # 単一クラス記号
                        collected_class_codes.add(info.get('class_code', ''))
            
            # 空文字を除外
            collected_class_codes.discard('')
            
            if collected_class_codes:
                cache_manager.set_class_codes(class_config['name'], list(collected_class_codes))
                log(f"✅ クラス記号を検出: {sorted(collected_class_codes)}")
        
        # 各学生フォルダから課題を収集
        assignments_set = set()
        
        log(f"\n🔍 課題フォルダスキャン開始...")
        log(f"   進捗状況を5人ごとに表示します")
        log("")
        
        scanned_count = 0
        for student_folder in student_folders:
            scanned_count += 1
            
            student_name = student_folder['name']
            
            # 進捗ログ(5人ごと + 処理中の学生名を常時表示)
            if scanned_count % 5 == 0:
                progress_msg = f"   📊 進捗: {scanned_count}/{total_students}人スキャン完了 (処理中: {student_name})"
                log(progress_msg)
            elif scanned_count == 1:
                # 最初の1人目は必ず表示
                log(f"   🔍 スキャン中: 1人目 {student_name}")
            elif scanned_count == total_students:
                # 最後の1人も必ず表示
                log(f"   🔍 スキャン中: {scanned_count}/{total_students}人目 {student_name} (最終)")
            
            student_path = f"{base_folder}/{student_folder['name']}"
            assignment_folders = api_client.get_assignment_folders(drive_id, student_path)
            
            for folder in assignment_folders:
                assignments_set.add(folder["name"])
        
        # 最終進捗を表示
        if scanned_count > 0:
            log(f"\n   ✅ スキャン完了: {scanned_count}/{total_students}人")
        
        # キャッシュを更新
        sorted_assignments = sorted(list(assignments_set))
        cache_manager.set(class_config['name'], sorted_assignments)
        log(f"✅ フルスキャン完了: {len(sorted_assignments)}個の課題を検出")
        
        return sorted_assignments
