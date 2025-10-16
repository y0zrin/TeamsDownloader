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
    """SharePoint側の学生名からOHSプレフィックスを削除してキーを作成"""
    cleaned = re.sub(r'^OHS\d+\s+', '', name)
    return cleaned.replace(' ', '').replace('　', '').strip()
