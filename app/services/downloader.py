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
        """未提出者を取得(クラス記号選択履歴を考慮)
        
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
        
        class_name = class_config['name']
        
        # 学生情報を取得
        students_info = self.cache.get_students_info()
        if not students_info:
            return [], "❌ 学生情報が見つかりません(students.csv/xlsxを配置してください)"
        
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
        
        # 学生リストをキャッシュから取得
        cached_students_list, _ = self.cache.get_students_list(class_name)
        
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
        
        # SharePoint上の学生リストから、実際にこのクラスにいる学生の情報を取得
        current_class_students = {}
        
        log(f"\n🔍 クラス内の学生情報を照合中...")
        
        for student in cached_students_list:
            student_name = student['name']
            cleaned_name = clean_student_name(student_name)
            name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
            
            if name_key not in students_info:
                continue
            
            # _get_student_infoと同じロジックで学生情報を取得
            matched = students_info[name_key]
            
            if isinstance(matched, list):
                # 複数クラス記号を持つ学生
                # クラス記号選択履歴を確認
                cached_selection = self.cache.get_class_code_selection(class_name, student_name)
                
                if cached_selection:
                    # 選択履歴がある場合
                    student_info = next((s for s in matched if s['class_code'] == cached_selection), None)
                    if student_info:
                        current_class_students[name_key] = student_info
                        log(f"   ✓ {student_name}: {cached_selection} (選択履歴)")
                else:
                    # 選択履歴がない場合は最初のものを使用
                    current_class_students[name_key] = matched[0]
                    log(f"   ✓ {student_name}: {matched[0]['class_code']} (デフォルト)")
            else:
                # 単一クラス記号
                current_class_students[name_key] = matched
                log(f"   ✓ {student_name}: {matched['class_code']}")
        
        log(f"📋 対象学生数: {len(current_class_students)}人")
        
        if len(current_class_students) == 0:
            log(f"⚠️ 警告: 該当する学生が名簿に見つかりません")
            return [], "該当する学生が名簿に見つかりません"
        
        # 提出者を検出
        log(f"\n🔍 提出状況確認中...")
        log(f"   進捗状況を10人ごとに表示します")
        log("")
        
        submitted_students = set()
        checked_count = 0
        
        for student in cached_students_list:
            if self.cancelled:
                return [], "キャンセルされました"
            
            student_name = student['name']
            cleaned_name = clean_student_name(student_name)
            name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
            
            # 対象学生でない場合はスキップ
            if name_key not in current_class_students:
                continue
            
            checked_count += 1
            student_path = f"{base_folder}/{student_name}"
            
            # 進捗表示(10人ごと)
            if checked_count % 10 == 0 or checked_count == len(current_class_students):
                log(f"   📊 進捗: {checked_count}/{len(current_class_students)}人確認完了")
            
            # 学生フォルダ内の課題をチェック
            assignment_folders = self.api_client.get_assignment_folders(drive_id, student_path)
            
            for assignment_folder in assignment_folders:
                folder_name = assignment_folder["name"]
                search_name = assignment_name.replace('/', '_')
                
                if search_name.lower() in folder_name.lower():
                    # 提出済みとしてマーク
                    submitted_students.add(name_key)
                    break
        
        log(f"✅ {len(submitted_students)}人が提出済み")
        
        # 名簿から未提出者を抽出
        unsubmitted = []
        for name_key, student_info in current_class_students.items():
            if name_key not in submitted_students:
                unsubmitted.append(student_info)
        
        # 出席番号順にソート
        unsubmitted.sort(key=lambda x: (x.get('class_code', ''), int(x.get('attendance_number', 0)) if x.get('attendance_number', '').isdigit() else 999))
        
        log(f"📋 未提出者: {len(unsubmitted)}人")
        
        if unsubmitted:
            log(f"\n未提出者詳細:")
            for student in unsubmitted:
                log(f"   - {student.get('student_name')} (クラスコード: {student.get('class_code')}, 出席番号: {student.get('attendance_number')})")
        
        return unsubmitted, None    
    
    def download_assignment(self, class_config, assignment_name, output_base_dir, 
                       progress_callback=None, class_code_dialog_callback=None,
                        selected_students=None):
        """課題をダウンロード(機能5: 特定学生選択対応 + IDベースマッピング対応 + 名前履歴対応)

        Args:
            class_config: クラス設定
            assignment_name: 課題名
            output_base_dir: 出力ベースディレクトリ
            progress_callback: 進捗コールバック関数
            class_code_dialog_callback: クラス記号選択ダイアログコールバック
            selected_students: 特定の学生のみダウンロードする場合の学生名リスト

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
            log(f"📥 課題ダウンロード開始(特定学生のみ): {assignment_name}")
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

        # 学生リストを統合（名前履歴対応）
        log(f"\n🔍 学生リストを取得中...")

        # 旧キャッシュを取得
        old_cached_list, _ = self.cache.get_students_list(class_config['name'])

        # SharePointから最新リストを取得
        student_folders = self.api_client.get_student_folders(drive_id, base_folder)
        log(f"✅ {len(student_folders)}人の学生フォルダを検出")

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
                    log(f"🔄 名前変更検出: {old_name} → {current_name} (ID: {student_id[:8]}...)")
                    student_id_map[student_id]['current_name'] = current_name
                    # 過去の名前リストに追加（重複チェック）
                    if current_name not in student_id_map[student_id]['past_names']:
                        student_id_map[student_id]['past_names'].append(current_name)
            else:
                # 新しいID
                student_id_map[student_id] = {
                    'id': student_id,
                    'current_name': current_name,
                    'past_names': [current_name]
                }

        # 統合リストを作成（全ての名前でスキャンできるように展開）
        cached_students_list = []
        for student_id, student_data in student_id_map.items():
            # 各名前ごとにエントリを作成
            for name in student_data['past_names']:
                cached_students_list.append({
                    'name': name,
                    'id': student_id,
                    'current_name': student_data['current_name']
                })

        log(f"💾 統合学生リスト: {len(student_id_map)}人（エントリ数: {len(cached_students_list)}）")

        # キャッシュを更新（次回用に最新リストを保存）
        simple_cache_list = []
        for student_id, student_data in student_id_map.items():
            simple_cache_list.append({
                'name': student_data['current_name'],
                'id': student_id
            })
        self.cache.set_students_list(class_config['name'], simple_cache_list)

        # 特定学生フィルタのセットを作成
        selected_students_set = None
        if selected_students:
            selected_students_set = set()
            for student_name in selected_students:
                cleaned = clean_student_name(student_name)
                selected_students_set.add(cleaned)
            log(f"🎯 ダウンロード対象: {len(selected_students_set)}人")

        student_data_list = []
        matched_count = 0
        unmatched_students = []

        # 課題提出フォルダをスキャン
        log(f"\n🔍 課題提出フォルダをスキャン中...")
        log(f"   進捗状況を5人ごとに表示します")
        log("")

        scanned_count = 0

        # キャッシュされた学生リストから課題提出者をフィルタ
        for student in cached_students_list:
            if self.cancelled:
                log("\n⚠️ ダウンロードがキャンセルされました")
                return 0, 0

            student_name = student['name']
            student_id = student['id']
            current_name = student.get('current_name', student_name)

            # 特定学生フィルタが有効な場合、対象外ならスキップ
            if selected_students_set:
                cleaned_name = clean_student_name(student_name)
                if cleaned_name not in selected_students_set:
                    continue
                
            # 除外チェック（IDベース）
            if self.cache.is_excluded_by_id(student_id):
                log(f"  ⏭️ {student_name}: 除外済み（スキップ）")
                continue
            
            scanned_count += 1

            # 進捗ログ(5人ごと)
            if scanned_count % 5 == 0:
                log(f"   📊 進捗: {scanned_count}/{len(cached_students_list)}人スキャン完了 (処理中: {student_name})")
            elif scanned_count == 1:
                log(f"   🔍 スキャン開始: 1人目 {student_name}")

            student_path = f"{base_folder}/{student_name}"

            # 学生フォルダ内の課題をチェック
            assignment_folders = self.api_client.get_assignment_folders(drive_id, student_path)

            for assignment_folder in assignment_folders:
                folder_name = assignment_folder["name"]
                search_name = assignment_name.replace('/', '_')

                if search_name.lower() in folder_name.lower():
                    # IDベースのマッピングを確認
                    cached_mapping = self.cache.get_name_mapping_by_id(student_id)
                    student_info = None

                    if cached_mapping and cached_mapping.get('status') == 'MAPPED':
                        # キャッシュから学生情報を復元
                        last_name = cached_mapping['last_known_name']
                        if last_name != student_name:
                            log(f"  🔄 マッピング名変更: {last_name} → {student_name}")

                        student_info = self._find_student_by_mapping(students_info, cached_mapping)
                        if student_info:
                            log(f"  ✅ {student_name}: IDマッピング適用 → {student_info['student_name']}")
                            matched_count += 1
                        else:
                            log(f"  ⚠️ {student_name}: マッピングされた学生が名簿から削除されています")

                    # 通常の名前照合
                    if not student_info:
                        student_info = self._get_student_info(
                            student_name, students_info, multi_class_students,
                            class_config['name'], class_code_dialog_callback, log,
                            student_id
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
                        'student_info': student_info,
                        'current_name': current_name
                    })
                    break
                
        # スキャン完了ログ
        if scanned_count > 0:
            log(f"\n   ✅ スキャン完了: {scanned_count}人")

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

        try:
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
        except Exception as e:
            log(f"\n❌ 学生一覧表示エラー: {e}")
            import traceback
            log(traceback.format_exc())

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
            current_name = student_data.get('current_name', student_name)

            # 保存先フォルダを決定
            if student_info:
                class_code = student_info['class_code']
                attendance_number = student_info['attendance_number']
                roster_name = student_info['student_name']

                try:
                    attendance_padded = f"{int(attendance_number):02d}"
                except (ValueError, TypeError):
                    attendance_padded = str(attendance_number)

                student_folder_name = f"{attendance_padded}_{roster_name}"
                student_output = os.path.join(output_folder, class_code, student_folder_name)

                # ログ出力
                if student_name != roster_name:
                    if student_name != current_name:
                        log(f"  📁 [{class_code}] {attendance_padded}_{roster_name} の提出物を処理中... (過去名: {student_name}, 現在: {current_name})")
                    else:
                        log(f"  📁 [{class_code}] {attendance_padded}_{roster_name} の提出物を処理中... (SharePoint: {student_name})")
                else:
                    log(f"  📁 [{class_code}] {attendance_padded}_{roster_name} の提出物を処理中...")
            else:
                student_output = os.path.join(output_folder, student_name)
                log(f"  📁 {student_name} の提出物を処理中...")

            # 課題フォルダ内のファイルを取得
            files = self.api_client.get_files_in_folder(drive_id, assignment_path)

            log(f"     ファイル数: {len(files)}個")
            if len(files) == 0:
                log(f"     ⚠️ ファイルが見つかりません: {assignment_path}")

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


    def _find_student_by_mapping(self, students_info, mapping):
        """マッピング情報から学生情報を検索"""
        target_class = mapping['class_code']
        target_number = mapping['attendance_number']

        for name_key, info in students_info.items():
            if isinstance(info, list):
                for item in info:
                    if (item.get('class_code') == target_class and
                        str(item.get('attendance_number')) == str(target_number)):
                        return item
            else:
                if (info.get('class_code') == target_class and
                    str(info.get('attendance_number')) == str(target_number)):
                    return info
        return None


    def _get_student_info(self, student_name, students_info, multi_class_students,
                     class_name, class_code_dialog_callback, log, student_id=None):
        """学生情報を取得(複数クラス対応 + IDベースマッピング対応)"""
        if not students_info:
            return None
        
        cleaned_name = clean_student_name(student_name)
        sharepoint_name_key = cleaned_name.replace(' ', '').replace('　', '').strip()
        
        if sharepoint_name_key not in students_info:
            # ★ 名前で見つからない場合、IDベースマッピングを提案
            if student_id and class_code_dialog_callback:
                log(f"  ❓ {student_name}: 名簿に見つかりません。マッピングダイアログを表示します")
                
                from gui.dialogs import NameMappingDialog
                
                # GUIスレッドでダイアログを表示
                dialog_result = {'selected': None}
                
                def show_dialog():
                    dialog = NameMappingDialog(None, student_name, students_info)
                    dialog_result['selected'] = dialog.show()
                
                # メインスレッドでダイアログを実行
                import threading
                if threading.current_thread() is threading.main_thread():
                    show_dialog()
                else:
                    # バックグラウンドスレッドの場合は、メインスレッドで実行
                    import tkinter as tk
                    root = tk._default_root
                    if root:
                        root.after(0, show_dialog)
                        # ダイアログが閉じるまで待機
                        while dialog_result['selected'] is None:
                            import time
                            time.sleep(0.1)
                
                selected = dialog_result['selected']
                
                if selected == "EXCLUDED":
                    self.cache.set_name_mapping_by_id(student_id, student_name, "EXCLUDED")
                    log(f"  ❌ {student_name}: 除外設定（ID保存）")
                    return None
                elif selected:
                    self.cache.set_name_mapping_by_id(student_id, student_name, selected)
                    log(f"  ✅ {student_name}: マッピング設定（ID保存）")
                    return selected
            
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