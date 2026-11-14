#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提出物の選別

同じ課題フォルダに再提出版が並んでいることがあるため、
「最新の提出物のみ」設定が有効なときは拡張子ごとに最新の1件だけを残す。
"""

import os

from core.api_client import parse_graph_timestamp


def get_modified_time(item):
    """アイテムの更新日時（UNIX時刻）を取得。不明なら0"""
    timestamp = parse_graph_timestamp(item.get("lastModifiedDateTime"))
    if timestamp is None:
        timestamp = parse_graph_timestamp(item.get("createdDateTime"))
    return timestamp if timestamp is not None else 0.0


def _sort_key(item):
    """更新日時 → 名前 の順で比較（同時刻でも結果がぶれないように）"""
    return (get_modified_time(item), str(item.get("name", "")))


def select_latest_folder(folders):
    """課題名に一致したフォルダが複数ある場合、最新のものを選ぶ"""
    if not folders:
        return None
    return max(folders, key=_sort_key)


def _extension(item):
    """拡張子を小文字で取得（拡張子なしは空文字）"""
    return os.path.splitext(str(item.get("name", "")))[1].lower()


def select_latest_files(files):
    """拡張子ごとに最新の1件だけを残す

    Args:
        files: SharePointのファイル情報リスト

    Returns:
        (kept, dropped)
            kept: 残したファイル（元の並び順）
            dropped: [(除外したファイル, 代わりに残した最新ファイル), ...]
    """
    if not files:
        return [], []

    newest_by_ext = {}
    for item in files:
        ext = _extension(item)
        current = newest_by_ext.get(ext)
        if current is None or _sort_key(item) > _sort_key(current):
            newest_by_ext[ext] = item

    kept = []
    dropped = []

    for item in files:
        newest = newest_by_ext[_extension(item)]
        if item is newest:
            kept.append(item)
        else:
            dropped.append((item, newest))

    return kept, dropped
