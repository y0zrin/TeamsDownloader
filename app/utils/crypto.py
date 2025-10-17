#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
暗号化ユーティリティ
"""

import os
import json

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


ENCRYPTION_KEY_FILE = "encryption.key"


def get_or_create_encryption_key():
    """暗号化キーを取得または生成"""
    if not ENCRYPTION_AVAILABLE:
        return None
    
    if os.path.exists(ENCRYPTION_KEY_FILE):
        try:
            with open(ENCRYPTION_KEY_FILE, 'rb') as f:
                return f.read()
        except:
            pass
    
    # 新しいキーを生成
    key = Fernet.generate_key()
    try:
        with open(ENCRYPTION_KEY_FILE, 'wb') as f:
            f.write(key)
        return key
    except:
        return None


def encrypt_data(data):
    """データを暗号化してバイト列で返す"""
    if not ENCRYPTION_AVAILABLE or not data:
        return None
    
    key = get_or_create_encryption_key()
    if not key:
        return None
    
    try:
        fernet = Fernet(key)
        json_str = json.dumps(data, ensure_ascii=False)
        encrypted_data = fernet.encrypt(json_str.encode('utf-8'))
        return encrypted_data
    except Exception as e:
        print(f"暗号化エラー: {e}")
        return None


def decrypt_data(encrypted_data):
    """暗号化されたデータを復号化"""
    if not ENCRYPTION_AVAILABLE or not encrypted_data:
        return None
    
    key = get_or_create_encryption_key()
    if not key:
        return None
    
    try:
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)
        data = json.loads(decrypted_data.decode('utf-8'))
        return data
    except Exception as e:
        print(f"復号化エラー: {e}")
        return None
