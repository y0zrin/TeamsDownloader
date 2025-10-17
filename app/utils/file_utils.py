#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ファイル操作ユーティリティ
"""

import os
import re


def sanitize_filename(filename):
    """ファイル名/フォルダ名に使えない文字を置き換える"""
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    return sanitized


def detect_excel_format(filepath):
    """Detect actual file format (check content, not extension)"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
            
            if header[:4] == b'PK\x03\x04':
                return 'xlsx'
            elif header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                return 'xls'
            else:
                return 'csv'
    except:
        if filepath.endswith('.csv'):
            return 'csv'
        elif filepath.endswith('.xlsx'):
            return 'xlsx'
        else:
            return 'xls'


def check_drm_protection(filepath):
    """Check if file is DRM protected"""
    try:
        import olefile
    except ImportError:
        return False
        
    try:
        with open(filepath, 'rb') as f:
            header = f.read(8)
        
        if header[:4] == b'PK\x03\x04':
            return False
        
        if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            try:
                import olefile
                ole = olefile.OleFileIO(filepath)
                for entry in ole.listdir():
                    stream_path = '/'.join(entry)
                    if 'DRM' in stream_path or 'DataSpaces' in stream_path:
                        ole.close()
                        return True
                ole.close()
            except:
                pass
        
        return False
    except:
        return False


def clean_student_name(name):
    """学生名を正規化してキーを作成（プレフィックスを除去して氏名のみで照合）
    
    SharePoint上の学生フォルダ名から、プレフィックス（出席番号、学籍番号など）を
    削除して、純粋な氏名のみを抽出します。
    
    対応するプレフィックスのパターン:
    - 01_山田太郎        → 山田太郎
    - 01-山田太郎        → 山田太郎
    - OHS12345山田太郎   → 山田太郎
    - OHS12345_山田太郎  → 山田太郎
    - AT12B543-01山田太郎 → 山田太郎
    - OHS12345JohnSmith  → JohnSmith (留学生対応)
    - 01_JohnSmith       → JohnSmith (留学生対応)
    """
    # スペース・全角スペースを削除
    name = str(name).replace(' ', '').replace('　', '').strip()
    
    # プレフィックスパターンを順番に試行
    
    # パターン1: 数字2桁 + アンダースコア/ハイフン (例: 01_山田太郎, 01-山田太郎, 01_JohnSmith)
    name = re.sub(r'^[0-9]{1,3}[_\-]', '', name)
    
    # パターン2: 英字+数字の組み合わせ + アンダースコア/ハイフン (例: OHS12345_山田太郎, AT12B543_山田太郎)
    name = re.sub(r'^[A-Za-z]+[0-9]+[A-Za-z0-9]*[_\-]', '', name)
    
    # パターン3: クラス記号-番号 (例: AT12B543-01山田太郎, AT12B543-01JohnSmith)
    name = re.sub(r'^[A-Za-z0-9]+-[0-9]+', '', name)
    
    # パターン4: 英数字の組み合わせ（区切り文字なし、5文字以上）
    # 日本語または大文字アルファベット（名前の開始）の前まで削除
    # 例: OHS12345山田太郎 → 山田太郎, OHS12345JohnSmith → JohnSmith
    name = re.sub(r'^[a-z]*[0-9]+[a-z0-9]*(?=[ぁ-んァ-ヶー一-龠]|[A-Z])', '', name, flags=re.IGNORECASE)
    
    return name
