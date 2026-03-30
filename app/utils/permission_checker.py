#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
トークン権限チェックユーティリティ
"""

import base64
import json
from datetime import datetime, timezone


# 削除操作に必要な書き込み系スコープ
WRITE_SCOPES = [
    "Files.ReadWrite.All",
    "Sites.ReadWrite.All",
    "Files.ReadWrite",
]


def check_token_permissions(token):
    """JWTアクセストークンを解析し、権限情報を返す

    Args:
        token: Microsoft Graph APIのアクセストークン（JWT形式）

    Returns:
        dict: 権限情報
            - has_write_permission (bool): 書き込み権限があるか
            - scopes (list): 付与されたスコープ一覧
            - write_scopes_found (list): 見つかった書き込みスコープ
            - write_scopes_missing (list): 不足している書き込みスコープ
            - user (str): ユーザー名
            - expires (str): トークン有効期限
            - is_expired (bool): 期限切れか
            - error (str|None): エラーメッセージ
    """
    try:
        payload = _decode_jwt_payload(token)
    except Exception as e:
        return {
            "has_write_permission": False,
            "scopes": [],
            "write_scopes_found": [],
            "write_scopes_missing": list(WRITE_SCOPES),
            "user": "不明",
            "expires": "不明",
            "is_expired": False,
            "error": f"トークンの解析に失敗しました: {e}",
        }

    # スコープ取得（委任: scp, アプリケーション: roles）
    scp_str = payload.get("scp", "")
    scopes = scp_str.split() if scp_str else []

    roles = payload.get("roles", [])
    if isinstance(roles, list):
        scopes.extend(roles)

    # 書き込みスコープの判定
    scopes_lower = [s.lower() for s in scopes]
    write_found = [s for s in WRITE_SCOPES if s.lower() in scopes_lower]
    write_missing = [s for s in WRITE_SCOPES if s.lower() not in scopes_lower]

    # ユーザー情報
    user = payload.get("upn") or payload.get("preferred_username") or payload.get("unique_name", "不明")

    # 有効期限
    exp = payload.get("exp")
    if exp:
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        expires_str = exp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        is_expired = datetime.now(timezone.utc) > exp_dt
    else:
        expires_str = "不明"
        is_expired = False

    return {
        "has_write_permission": len(write_found) > 0,
        "scopes": scopes,
        "write_scopes_found": write_found,
        "write_scopes_missing": write_missing,
        "user": user,
        "expires": expires_str,
        "is_expired": is_expired,
        "error": None,
    }


def _decode_jwt_payload(token):
    """JWTのペイロード部分をデコードする"""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("JWTの形式が不正です（3パートではありません）")

    payload_b64 = parts[1]
    # Base64urlのパディング補完
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding

    payload_bytes = base64.urlsafe_b64decode(payload_b64)
    return json.loads(payload_bytes)
