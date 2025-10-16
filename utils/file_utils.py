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
    """学生名を正規化してキーを作成（氏名のみで照合）
    
    変更点: プレフィックス（OHS数字など）の削除処理を削除し、
            氏名のみでマッチングするように変更
    """
    # スペース・全角スペースを削除して正規化
    return str(name).replace(' ', '').replace('　', '').strip()
