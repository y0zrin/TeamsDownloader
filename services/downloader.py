#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題ダウンロードサービス
"""

import os
from utils.file_utils import sanitize_filename, clean_student_name


class DownloadService:
    """課題ダウンロードを管理するサービス"""
    
    def __init__(self, api_client, cache_manager):
        self.api_client = api_client
        self.cache = cache_manager
        self.cancelled = False
    
    def cancel(self):
        """ダウンロードをキャンセル"""
        self.cancelled = True
    
    def reset_cancel(self):
        """キャンセルフラグをリセット"""
        self.cancelled = False
    
    def get_unsubmitted_students(self, class_config, assignment_name, progress_callback=None):
        """未提出者を取得（新機能4）
        
        Returns:
            tuple: (未提出者リスト, エラーメッセージ)
        """
        def log(msg):
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)
        
        log(f"\n{'='*50}")
        log(f"📊 未提出者確認: {assignment_name}")
        log(f"{'='*50}")
        
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
        
        # 学生情報を取得
        students_info = self.cache.get_students_info()
        if not students_info:
            return [], "❌ 学生情報が見つかりません（students.csv/xlsxを配置してください）"
        
        # 学生リストをキャッシュから取得
        cached_students_list, _ = self.cache.get_students_list(class_config['name'])
        
        if not cached_students_list:
            # キャッシュがない場合はスキャン
            log("🔍 学生フォルダをスキャン中...")
            cached_students_list = []
            student_folders = self.api_client.get_student_folders(drive_id, base_folder)
            for student_folder in student_folders:
                cached_students_list.append({
                    'name': student_folder['name'],
                    'id': student_folder['id']
                })
        
        # 提出者を検出
        submitted_students = set()
        for student in cached_students_list:
            if self.cancelled:
                return [], "キャンセルされました"
            
            student_name = student['name']
            student_path = f"{base_folder}/{student_name}"
            
            # 学生フォルダ内の課題をチェック
            assignment_folders = self.api_client.get_assignment_folders(drive_id, student_path)
            
            for assignment_folder in assignment_folders:
                folder_name = assignment_folder["name"]
                search_name = assignment_name.replace('/', '_')
                
                if search_name.lower() in folder_name.lower():
                    # 提出済みとしてマーク
                    cleaned_name = clean_student_name(student_name)
                    submitted_students.add(cleaned_name)
                    break
        
        log(f"✅ {len(submitted_students)}人が提出済み")
        
        # 名簿から未提出者を抽出
        unsubmitted = []
        multi_class_students = self.cache.get_multi_class_students()
        
        for name_key, info in students_info.items():
            if name_key not in submitted_students:
                # 複数クラス記号を持つ学生の処理
                if isinstance(info, list):
                    for student_info in info:
                        unsubmitted.append(student_info)
                else:
                    unsubmitted.append(info)
        
        # クラス記号でフィルタリング（現在のクラスに所属する学生のみ）
        class_name = class_config['name']
        filtered_unsubmitted = []
        
        for student_info in unsubmitted:
            # クラス名からクラス記号を推定（例: OHC25-AT12B543 → AT12B543）
            class_code_suffix = class_name.split('-')[-1] if '-' in class_name else class_name
            student_class_code = student_info.get('class_code', '')
            
            # 部分一致で判定（最初の4文字が一致すれば同じクラスとみなす）
            if student_class_code[:4] == class_code_suffix[:4]:
                filtered_unsubmitted.append(student_info)
        
        # 出席番号順にソート
        filtered_unsubmitted.sort(key=lambda x: (x.get('class_code', ''), int(x.get('attendance_number', 0)) if x.get('attendance_number', '').isdigit() else 999))
        
        log(f"📋 未提出者: {len(filtered_unsubmitted)}人")
        
        return filtered_unsubmitted, None
    
    def download_assignment(self, class_config, assignment_name, output_base_dir, 
                           progress_callback=None, class_code_dialog_callback=None,
                           selected_students=None):
        """課題をダウンロード（機能5: 特定学生選択対応）
        
        Args:
            class_config: クラス設定
            assignment_name: 課題名
            output_base_dir: 出力ベースディレクトリ
            progress_callback: 進捗コールバック関数
            class_code_dialog_callback: クラス記号選択ダイアログコールバック
            selected_students: 特定の学生のみダウンロードする場合の学生名リスト（新機能5）
        
        Returns:
            tuple: (成功数, 学生数)
        """
        self.reset_cancel()
        
        def log(msg):
            if progress_callback:
                progress_callback(msg)
            else:
                print(msg)
        
        log(f"\n{'='*50}")
        if selected_students:
            log(f"📥 課題ダウンロード開始（特定学生のみ）: {assignment_name}")
        else:
            log(f"📥 課題ダウンロード開始: {assignment_name}")
        log(f"{'='*50}")
        
        # 出力フォルダを準備
        safe_assignment_name = sanitize_filename(assignment_name)
        output_folder = os.path.join(output_base_dir, class_config['name'], safe_assignment_name)
        os.makedirs(output_folder, exist_ok=True)
        
        log(f"\n💾 保存先: {output_folder}")
        
        # サイトIDとドライブIDを取得
        site_id = self.api_client.get_site_id(class_config["site_path"])
        if not site_id:
            log("❌ サイトIDの取得に失敗")
            return 0, 0
        
        drive_id, drive_name = self.api_client.get_drive_id(site_id)
        if not drive_id:
            log("❌ ドライブIDの取得に失敗")
            return 0, 0
        
        log("✅ SharePointに接続しました")
        
        # ドライブ名に応じてベースフォルダを設定
        if drive_name == "Student Work":
            base_folder = "Working files"
        else:
            base_folder = "Student Work/Working files"
        
        log(f"📂 フォルダパス: {drive_name}/{base_folder}")
        
        # 学生情報を取得
        students_info = self.cache.get_students_info()
        multi_class_students = self.cache.get_multi_class_students()
        
        # 学生リストをキャッシュから取得
        cached_students_list, cache_updated = self.cache.get_students_list(class_config['name'])
        
        # 特定学生フィルタのセットを作成
        selected_students_set = None
        if selected_students:
            selected_students_set = set()
            for student_name in selected_students:
                # 名簿上の名前をクリーンにしてセットに追加
                cleaned = clean_student_name(student_name)
                selected_students_set.add(cleaned)
            log(f"🎯 ダウンロード対象: {len(selected_students_set)}人")
        
        student_data_list = []
        matched_count = 0
        unmatched_students = []
        
        if cached_students_list:
            log(f"💾 学生リストをキャッシュから読み込み中...")
            log(f"✅ キャッシュから{len(cached_students_list)}人の学生リストを取得")
            
            # キャッシュされた学生リストから課題提出者をフィルタ
            for student in cached_students_list:
                if self.cancelled:
                    log("\n⚠️ ダウンロードがキャンセルされました")
                    return 0, 0
                
                student_name = student['name']
                
                # 特定学生フィルタが有効な場合、対象外ならスキップ
                if selected_students_set:
                    cleaned_name = clean_student_name(student_name)
                    if cleaned_name not in selected_students_set:
                        continue
                
                student_id = student['id']
                student_path = f"{base_folder}/{student_name}"
                
                # 学生フォルダ内の課題をチェック
                assignment_folders = self.api_client.get_assignment_folders(drive_id, student_path)
                
                for assignment_folder in assignment_folders:
                    folder_name = assignment_folder["name"]
                    search_name = assignment_name.replace('/', '_')
                    
                    if search_name.lower() in folder_name.lower():
                        # 学生情報を取得
                        student_info = self._get_student_info(
                            student_name, students_info, multi_class_students,
                            class_config['name'], class_code_dialog_callback, log
                        )
                        
                        if student_info:
                            matched_count += 1
                        else:
                            cleaned_name = clean_student_name(student_name)
                            sharepoint_name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
                            unmatched_students.append({
                                'name': student_name,
                                'cleaned': cleaned_name,
                                'key': sharepoint_name_key
                            })
                        
                        student_data_list.append({
                            'student_name': student_name,
                            'student_path': student_path,
                            'folder_name': folder_name,
                            'assignment_path': f"{student_path}/{folder_name}",
                            'student_info': student_info
                        })
                        break
        else:
            # キャッシュがない場合は従来通りスキャン
            log(f"🔍 学生データをスキャン中...")
            
            student_folders = self.api_client.get_student_folders(drive_id, base_folder)
            
            for student_folder in student_folders:
                if self.cancelled:
                    log("\n⚠️ ダウンロードがキャンセルされました")
                    return 0, 0
                
                student_name = student_folder["name"]
                
                # 特定学生フィルタが有効な場合、対象外ならスキップ
                if selected_students_set:
                    cleaned_name = clean_student_name(student_name)
                    if cleaned_name not in selected_students_set:
                        continue
                
                student_path = f"{base_folder}/{student_name}"
                
                assignment_folders = self.api_client.get_assignment_folders(drive_id, student_path)
                
                for assignment_folder in assignment_folders:
                    folder_name = assignment_folder["name"]
                    search_name = assignment_name.replace('/', '_')
                    
                    if search_name.lower() in folder_name.lower():
                        # 学生情報を取得
                        student_info = self._get_student_info(
                            student_name, students_info, multi_class_students,
                            class_config['name'], class_code_dialog_callback, log
                        )
                        
                        if student_info:
                            matched_count += 1
                        else:
                            cleaned_name = clean_student_name(student_name)
                            sharepoint_name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
                            unmatched_students.append({
                                'name': student_name,
                                'cleaned': cleaned_name,
                                'key': sharepoint_name_key
                            })
                        
                        student_data_list.append({
                            'student_name': student_name,
                            'student_path': student_path,
                            'folder_name': folder_name,
                            'assignment_path': f"{student_path}/{folder_name}",
                            'student_info': student_info
                        })
                        break
        
        student_count = len(student_data_list)
        
        # マッチング結果を表示
        if students_info:
            log(f"\n📊 マッチング結果:")
            log(f"   課題提出者: {student_count}人")
            log(f"   名簿とマッチ: {matched_count}人")
            if len(unmatched_students) > 0:
                log(f"   名簿になし: {len(unmatched_students)}人")
        
        # 検出された学生の一覧を表示
        log(f"\n📋 検出された学生一覧 ({student_count}人):")
        log("="*60)
        
        if students_info:
            # 学生情報がある学生を出席番号順にソート
            with_info = [s for s in student_data_list if s['student_info']]
            
            def get_sort_key(student):
                try:
                    return int(student['student_info']['attendance_number'])
                except (ValueError, TypeError):
                    return float('inf')
            
            with_info.sort(key=get_sort_key)
            without_info = [s for s in student_data_list if not s['student_info']]
            without_info.sort(key=lambda x: x['student_name'])
            student_data_list = with_info + without_info
            
            for idx, student_data in enumerate(with_info, 1):
                info = student_data['student_info']
                try:
                    num = f"{int(info['attendance_number']):02d}"
                except:
                    num = info['attendance_number']
                log(f"   {idx:2d}. [{info['class_code']}] {num} {student_data['student_name']}")
            
            if without_info:
                log(f"\n   名簿外の学生:")
                for idx, student_data in enumerate(without_info, 1):
                    log(f"   {idx:2d}. {student_data['student_name']}")
        else:
            student_data_list.sort(key=lambda x: x['student_name'])
            for idx, student_data in enumerate(student_data_list, 1):
                log(f"   {idx:2d}. {student_data['student_name']}")
        
        log("="*60)
        log(f"\n📥 ダウンロード開始...")
        
        # ダウンロード実行
        download_count = 0
        for student_data in student_data_list:
            if self.cancelled:
                log("\n⚠️ ダウンロードがキャンセルされました")
                return download_count, student_count
            
            student_name = student_data['student_name']
            assignment_path = student_data['assignment_path']
            student_info = student_data['student_info']
            
            # 保存先フォルダを決定
            if student_info:
                class_code = student_info['class_code']
                attendance_number = student_info['attendance_number']
                
                try:
                    attendance_padded = f"{int(attendance_number):02d}"
                except (ValueError, TypeError):
                    attendance_padded = str(attendance_number)
                
                student_folder_name = f"{attendance_padded}_{student_name}"
                student_output = os.path.join(output_folder, class_code, student_folder_name)
                
                log(f"  📁 [{class_code}] {attendance_padded}_{student_name} の提出物を処理中...")
            else:
                student_output = os.path.join(output_folder, student_name)
                log(f"  📁 {student_name} の提出物を処理中...")
            
            # 課題フォルダ内のファイルを取得
            files = self.api_client.get_files_in_folder(drive_id, assignment_path)
            
            for file_item in files:
                if self.cancelled:
                    log("\n⚠️ ダウンロードがキャンセルされました")
                    return download_count, student_count
                
                file_name = file_item["name"]
                file_path = f"{assignment_path}/{file_name}"
                save_file_path = os.path.join(student_output, file_name)
                
                if self.api_client.download_file(drive_id, file_path, save_file_path):
                    download_count += 1
        
        if student_count == 0:
            log(f"\n⚠️ 課題「{assignment_name}」が見つかりませんでした")
        else:
            log(f"\n✅ ダウンロード完了!")
            log(f"   学生数: {student_count}人")
            log(f"   ファイル数: {download_count}個")
            log(f"   保存先: {output_folder}")
        
        return download_count, student_count
    
    def _get_student_info(self, student_name, students_info, multi_class_students,
                         class_name, class_code_dialog_callback, log):
        """学生情報を取得(複数クラス対応)"""
        if not students_info:
            return None
        
        cleaned_name = clean_student_name(student_name)
        sharepoint_name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
        
        if sharepoint_name_key not in students_info:
            return None
        
        # まず複数クラスキャッシュをチェック
        if sharepoint_name_key in multi_class_students:
            matched = multi_class_students[sharepoint_name_key]
            log(f"  🔍 {student_name}: 複数クラス検出 (専用キャッシュ)")
            codes = [s['class_code'] for s in matched]
            log(f"     選択肢: {codes}")
        else:
            matched = students_info[sharepoint_name_key]
        
        # 複数クラス記号がある場合
        if isinstance(matched, list):
            codes = [s['class_code'] for s in matched]
            
            # キャッシュを確認
            cached_selection = self.cache.get_class_code_selection(class_name, student_name)
            
            if cached_selection:
                student_info = next((s for s in matched if s['class_code'] == cached_selection), matched[0])
                log(f"   ✅ キャッシュから適用: {cached_selection}")
                return student_info
            else:
                # ダイアログで選択
                if class_code_dialog_callback:
                    log(f"   ❓ ダイアログで選択を要求中...")
                    selected_code = class_code_dialog_callback(student_name, codes, class_name)
                    
                    if selected_code:
                        student_info = next((s for s in matched if s['class_code'] == selected_code), matched[0])
                        # 選択を保存
                        self.cache.set_class_code_selection(class_name, student_name, selected_code)
                        log(f"   ✅ 選択: {selected_code}")
                        return student_info
                    else:
                        # スキップされた場合は最初のものを使用
                        student_info = matched[0]
                        log(f"   ⏭️ スキップ: {matched[0]['class_code']}を使用")
                        return student_info
                else:
                    # コールバックがない場合は最初のものを使用
                    return matched[0]
        else:
            return matched
