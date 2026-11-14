#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダウンロード除外パターン

SharePoint上のファイル名がパターンに一致したら、そのファイルはダウンロードしない。
（zipファイルは1つのファイルとして転送されるため、zipの中身は対象外）
"""

import fnmatch

# 設定ダイアログに出す候補（初期状態では何も除外しない）
SUGGESTED_PATTERNS = [
    ("*.mp4", "動画ファイル"),
    ("*.mov", "動画ファイル"),
    ("*.avi", "動画ファイル"),
    ("*.iso", "ディスクイメージ"),
    ("*.exe", "実行ファイル"),
    ("*.msi", "インストーラ"),
    ("*.psd", "Photoshopファイル"),
    ("*.mp3", "音声ファイル"),
    ("*.wav", "音声ファイル"),
    ("Thumbs.db", "Windowsのサムネイルキャッシュ"),
    ("desktop.ini", "Windowsのフォルダ設定"),
    (".DS_Store", "macOSのフォルダ設定"),
]


def normalize_pattern(pattern):
    """入力されたパターンを整形

    拡張子だけ（".mp4"）を書かれた場合は "*.mp4" として扱う。
    """
    pattern = str(pattern).strip()
    if not pattern:
        return ""

    # ".mp4" → "*.mp4"（ただし ".DS_Store" のようなファイル名はそのまま）
    if pattern.startswith('.') and '*' not in pattern and '?' not in pattern:
        if '.' not in pattern[1:]:
            return f"*{pattern}"

    return pattern


def normalize_patterns(patterns):
    """パターンリストを整形（空要素と重複を除去、順序は維持）"""
    normalized = []
    seen = set()

    for pattern in patterns or []:
        value = normalize_pattern(pattern)
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)

    return normalized


def match_pattern(file_name, patterns):
    """ファイル名に一致した除外パターンを返す（大文字小文字は無視）

    Args:
        file_name: ファイル名
        patterns: 除外パターンのリスト

    Returns:
        一致したパターン。一致しなければNone
    """
    if not patterns or not file_name:
        return None

    name = str(file_name).lower()

    for pattern in patterns:
        value = normalize_pattern(pattern)
        if not value:
            continue
        if fnmatch.fnmatch(name, value.lower()):
            return value

    return None


def is_excluded(file_name, patterns):
    """ファイルが除外対象かどうか"""
    return match_pattern(file_name, patterns) is not None


def split_by_exclusion(files, patterns):
    """ファイルリストを (ダウンロード対象, 除外) に分ける

    Args:
        files: SharePointのファイル情報リスト（"name" を持つdict）
        patterns: 除外パターンのリスト

    Returns:
        (targets, excluded): excluded は (ファイル情報, 一致パターン) のリスト
    """
    if not patterns:
        return list(files), []

    targets = []
    excluded = []

    for file_item in files:
        pattern = match_pattern(file_item.get("name", ""), patterns)
        if pattern:
            excluded.append((file_item, pattern))
        else:
            targets.append(file_item)

    return targets, excluded
