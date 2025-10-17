#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
課題キャッシュ管理
"""

import os
import json
from datetime import datetime, timedelta
from utils.crypto import ENCRYPTION_AVAILABLE, encrypt_data, decrypt_data
from core.students import load_students_info


# フォントサイズの定義（5段階） - 変化を大きく調整
FONT_SIZES = {
    'smallest': {'ui': 8, 'log': 7, 'list': 9},    # 最小はそのまま
    'small': {'ui': 10, 'log': 9, 'list': 11},     # デフォルト（+1）
    'medium': {'ui': 12, 'log': 11, 'list': 13},   # 中（+2）
    'large': {'ui': 14, 'log': 13, 'list': 15},    # 大（+2）
    'largest': {'ui': 16, 'log': 15, 'list': 17},  # 最大（+2）
}

DEFAULT_FONT_SIZE = 'small'  # 現在は2番目に小さい状態
DEFAULT_DOWNLOAD_PATH = '../'  # デフォルトダウンロード先


class AssignmentCache:
    """課題一覧のキャッシュ管理"""
    
    def __init__(self, cache_file="assignments_cache.json", cache_hours=24):
        self.cache_file = cache_file
        self.encrypted_cache_file = "assignments_cache.dat"
        self.cache_hours = cache_hours
        self.cache_data = self.load_cache()
    
    def load_cache(self):
        """キャッシュファイルを読み込む"""
        # 1. 暗号化キャッシュを優先的に読み込み
        if ENCRYPTION_AVAILABLE and os.path.exists(self.encrypted_cache_file):
            try:
                with open(self.encrypted_cache_file, 'rb') as f:
                    encrypted_data = f.read()
                
                cache_data = decrypt_data(encrypted_data)
                if cache_data:
                    return cache_data
            except Exception as e:
                print(f"暗号化キャッシュ読み込みエラー: {e}")
        
        # 2. 平文キャッシュを読み込み(後方互換性)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 平文から読み込んだ場合は暗号化版に移行
                if ENCRYPTION_AVAILABLE:
                    print("💾 キャッシュを暗号化版に移行中...")
                    temp_data = cache_data
                    self.cache_data = temp_data
                    self.save_cache()
                    # 古い平文ファイルを削除
                    try:
                        os.remove(self.cache_file)
                        print("✅ 古いキャッシュファイルを削除しました")
                    except:
                        pass
                
                return cache_data
            except Exception as e:
                print(f"平文キャッシュ読み込みエラー: {e}")
        
        return {}
    
    def save_cache(self):
        """キャッシュファイルに保存"""
        # 暗号化が利用可能な場合
        if ENCRYPTION_AVAILABLE:
            encrypted_data = encrypt_data(self.cache_data)
            if encrypted_data:
                try:
                    with open(self.encrypted_cache_file, 'wb') as f:
                        f.write(encrypted_data)
                    return
                except Exception as e:
                    print(f"暗号化キャッシュ保存エラー: {e}")
        
        # 暗号化が利用不可の場合は平文で保存
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")
    
    def get(self, class_name):
        """キャッシュから課題一覧を取得"""
        if class_name in self.cache_data:
            cache_entry = self.cache_data[class_name]
            return cache_entry['assignments'], cache_entry['last_updated']
        return None, None
    
    def get_cached_assignments(self, class_name):
        """既存のキャッシュされた課題一覧を取得(有効期限無視)"""
        if class_name in self.cache_data:
            return set(self.cache_data[class_name]['assignments'])
        return set()
    
    def set(self, class_name, assignments):
        """課題一覧をキャッシュに保存"""
        now = datetime.now()
        expires_at = now + timedelta(hours=self.cache_hours)
        
        self.cache_data[class_name] = {
            'assignments': assignments,
            'last_updated': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'scan_mode': 'full'
        }
        self.save_cache()
    
    def update_incremental(self, class_name, new_assignments):
        """増分更新:新しい課題を追加"""
        if class_name in self.cache_data:
            existing = set(self.cache_data[class_name]['assignments'])
            combined = existing.union(new_assignments)
            
            now = datetime.now()
            expires_at = now + timedelta(hours=self.cache_hours)
            
            self.cache_data[class_name] = {
                'assignments': sorted(list(combined)),
                'last_updated': now.isoformat(),
                'expires_at': expires_at.isoformat(),
                'scan_mode': 'incremental'
            }
        else:
            self.set(class_name, sorted(list(new_assignments)))
        
        self.save_cache()
        return len(new_assignments - self.get_cached_assignments(class_name))
    
    def invalidate(self, class_name):
        """特定のクラスのキャッシュを無効化"""
        if class_name in self.cache_data:
            del self.cache_data[class_name]
            self.save_cache()
    
    def clear_all(self):
        """すべてのキャッシュをクリア（設定は保持）"""
        # 保持する設定
        font_size = self.cache_data.get('font_size', DEFAULT_FONT_SIZE)
        download_path = self.cache_data.get('download_path', DEFAULT_DOWNLOAD_PATH)
        cache_version = self.cache_data.get('_cache_version', 2)
    
        # キャッシュをクリア
        self.cache_data = {}
    
        # 設定を復元
        self.cache_data['font_size'] = font_size
        self.cache_data['download_path'] = download_path
        self.cache_data['_cache_version'] = cache_version
    
        self.save_cache()
    
    def get_students_list(self, class_name):
        """クラスの学生リストをキャッシュから取得"""
        cache_key = f"students_{class_name}"
        
        if cache_key in self.cache_data:
            cache_entry = self.cache_data[cache_key]
            return cache_entry['students_list'], cache_entry['last_updated']
        return None, None
    
    def set_students_list(self, class_name, students_list):
        """クラスの学生リストをキャッシュに保存"""
        cache_key = f"students_{class_name}"
        now = datetime.now()
        expires_at = now + timedelta(hours=self.cache_hours)
        
        self.cache_data[cache_key] = {
            'students_list': students_list,
            'last_updated': now.isoformat(),
            'expires_at': expires_at.isoformat()
        }
        self.save_cache()
    
    def get_students_info(self, show_dialog_if_missing=False):
        """学生情報をキャッシュから取得(キャッシュ優先)"""
        from core.students import ENCRYPTED_STUDENTS_FILE
        
        cache_key = "students_info"
        
        # 1. まずキャッシュを確認
        if cache_key in self.cache_data:
            cache_entry = self.cache_data[cache_key]
            
            # 暗号化キャッシュの場合
            if cache_entry.get('filename') == ENCRYPTED_STUDENTS_FILE:
                if ENCRYPTION_AVAILABLE and os.path.exists(ENCRYPTED_STUDENTS_FILE):
                    # ファイルの更新時刻をチェック
                    current_mtime = os.path.getmtime(ENCRYPTED_STUDENTS_FILE)
                    cached_mtime = cache_entry.get('file_mtime', 0)
                    
                    if current_mtime == cached_mtime:
                        # キャッシュが最新
                        return cache_entry['students_info']
            
            # 通常ファイルのキャッシュの場合
            elif cache_entry.get('filename') in ["students.csv", "students.xlsx"]:
                cached_filename = cache_entry.get('filename', '')
                if os.path.exists(cached_filename):
                    # ファイルの更新時刻をチェック
                    current_mtime = os.path.getmtime(cached_filename)
                    cached_mtime = cache_entry.get('file_mtime', 0)
                    
                    if current_mtime == cached_mtime:
                        # キャッシュが最新
                        return cache_entry['students_info']
        
        # 2. キャッシュがない、または古い場合はファイルから読み込み
        students_info = load_students_info()
        
        if students_info:
            # どのファイルから読み込んだかを特定
            filename = None
            if ENCRYPTION_AVAILABLE and os.path.exists(ENCRYPTED_STUDENTS_FILE):
                filename = ENCRYPTED_STUDENTS_FILE
            elif os.path.exists("students.csv"):
                filename = "students.csv"
            elif os.path.exists("students.xlsx"):
                filename = "students.xlsx"
            
            if filename:
                self.cache_data[cache_key] = {
                    'students_info': students_info,
                    'filename': filename,
                    'file_mtime': os.path.getmtime(filename),
                    'cached_at': datetime.now().isoformat(),
                    'encrypted': filename == ENCRYPTED_STUDENTS_FILE
                }
                self.save_cache()
        
        return students_info
    
    def get_class_code_selection(self, class_name, student_name):
        """保存されたクラス記号選択を取得"""
        cache_key = f"class_selection_{class_name}_{student_name}"
        return self.cache_data.get(cache_key)
    
    def set_class_code_selection(self, class_name, student_name, selected_code):
        """クラス記号選択を保存"""
        cache_key = f"class_selection_{class_name}_{student_name}"
        self.cache_data[cache_key] = selected_code
        self.save_cache()
    
    def get_multi_class_students(self):
        """複数クラス記号を持つ学生のキャッシュを取得"""
        if 'multi_class_students' not in self.cache_data:
            return self.build_multi_class_cache()
        return self.cache_data.get('multi_class_students', {})
    
    def build_multi_class_cache(self):
        """複数クラス記号を持つ学生の専用キャッシュを構築"""
        # 学生情報から複数クラス記号を持つ学生を抽出
        students_info = self.get_students_info()
        
        if not students_info:
            return {}
        
        multi_class_students = {}
        
        # students_infoから複数クラス（リスト形式）の学生を抽出
        for name_key, info in students_info.items():
            if isinstance(info, list):
                # 既に複数クラス記号を持つ学生として認識されている
                multi_class_students[name_key] = info
        
        # キャッシュに保存
        if multi_class_students:
            self.cache_data['multi_class_students'] = multi_class_students
            self.save_cache()
        
        return multi_class_students
    
    # ========== 新機能2: フォントサイズ設定 ==========
    
    def get_font_size(self):
        """フォントサイズ設定を取得"""
        return self.cache_data.get('font_size', DEFAULT_FONT_SIZE)
    
    def set_font_size(self, size):
        """フォントサイズ設定を保存"""
        if size in FONT_SIZES:
            self.cache_data['font_size'] = size
            self.save_cache()
            return True
        return False
    
    def get_font_config(self):
        """現在のフォント設定を取得"""
        size_key = self.get_font_size()
        return FONT_SIZES.get(size_key, FONT_SIZES[DEFAULT_FONT_SIZE])
    
    # ========== ダウンロード先設定 ==========
    
    def get_download_path(self):
        """ダウンロード先パスを取得"""
        return self.cache_data.get('download_path', DEFAULT_DOWNLOAD_PATH)
    
    def set_download_path(self, path):
        """ダウンロード先パスを保存"""
        self.cache_data['download_path'] = path
        self.save_cache()
        return True
    
    def reset_download_path(self):
        """ダウンロード先を初期設定に戻す"""
        self.cache_data['download_path'] = DEFAULT_DOWNLOAD_PATH
        self.save_cache()
        return DEFAULT_DOWNLOAD_PATH

    # ========== クラス記号キャッシュ ==========
    
    def get_class_codes(self, class_name):
        """クラスに含まれるクラス記号リストを取得"""
        cache_key = f"class_codes_{class_name}"
        return self.cache_data.get(cache_key, None)
    
    def set_class_codes(self, class_name, class_codes_list):
        """クラスに含まれるクラス記号リストを保存"""
        cache_key = f"class_codes_{class_name}"
        self.cache_data[cache_key] = list(set(class_codes_list))  # 重複除去
        self.save_cache()