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
    
    改善版：名前の開始位置を検出し、それより前を全てプレフィックスとして除去
    
    対応例:
    - 01_山田太郎        → 山田太郎
    - 01-山田太郎        → 山田太郎
    - 01 山田太郎        → 山田太郎 (スペース対応)
    - OHS12345山田太郎   → 山田太郎
    - OHS12345_山田太郎  → 山田太郎
    - AT12B543-01山田太郎 → 山田太郎
    - 01-OHS12345山田太郎 → 山田太郎 (複合プレフィックス)
    - OHS12345JohnSmith  → JohnSmith (留学生対応)
    - 01_JohnSmith       → JohnSmith
    """
    # スペース・全角スペースを削除
    name = str(name).replace(' ', '').replace('　', '').strip()
    
    # 日本語文字（ひらがな・カタカナ・漢字）または
    # 大文字始まりのアルファベット（名前の開始）を検出
    match = re.search(r'[ぁ-んァ-ヶー一-龠]|[A-Z][a-z]', name)
    
    if match:
        # 名前の開始位置以降を抽出
        return name[match.start():]
    
    # マッチしない場合（プレフィックスのみ、または全て小文字など）はそのまま返す
    return name
