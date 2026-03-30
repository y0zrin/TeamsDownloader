#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
アップデート確認のテスト

1. GitHub Releases API の応答を確認
2. バージョン比較ロジックをテスト
"""

import requests
from core.version import VERSION, RELEASES_API_URL, compare_versions


def main():
    print("=" * 50)
    print("アップデート確認テスト")
    print("=" * 50)
    print(f"\n現在のバージョン: v{VERSION}")
    print(f"API URL: {RELEASES_API_URL}")

    # API呼び出し
    print(f"\n--- GitHub Releases API 応答 ---")
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(RELEASES_API_URL, headers=headers, timeout=5)
    except Exception as e:
        print(f"接続エラー: {e}")
        return

    print(f"ステータス: {response.status_code}")

    if response.status_code == 404:
        print("リリースが見つかりません（まだ作成されていない）")
        print("\n→ アプリ側の動作: 何も表示しない（正常）")
        test_compare_only()
        return

    if response.status_code != 200:
        print(f"エラー: {response.text[:200]}")
        return

    data = response.json()
    tag = data.get("tag_name", "")
    latest = tag.lstrip("v")
    name = data.get("name", "")
    body = data.get("body", "")
    html_url = data.get("html_url", "")
    prerelease = data.get("prerelease", False)
    draft = data.get("draft", False)

    print(f"\nタグ: {tag}")
    print(f"タイトル: {name}")
    print(f"プレリリース: {prerelease}")
    print(f"ドラフト: {draft}")
    print(f"URL: {html_url}")
    if body:
        print(f"リリースノート:\n  {body[:200]}")

    # バージョン比較
    print(f"\n--- バージョン比較 ---")
    print(f"現在: v{VERSION}")
    print(f"最新: v{latest}")

    result = compare_versions(VERSION, latest)
    if result < 0:
        print(f"→ アップデートあり（ダイアログが表示される）")
    elif result == 0:
        print(f"→ 最新バージョン（ログに「最新バージョンです」と表示）")
    else:
        print(f"→ 現在の方が新しい（ログに「最新バージョンです」と表示）")

    test_compare_only()


def test_compare_only():
    """バージョン比較ロジックのみテスト"""
    print(f"\n--- compare_versions テスト ---")
    cases = [
        ("1.1.0", "1.1.0", "同じ → 通知なし"),
        ("1.1.0", "1.2.0", "古い → 通知あり"),
        ("1.1.0", "1.0.0", "新しい → 通知なし"),
        ("1.1.0", "2.0.0", "メジャー更新 → 通知あり"),
    ]
    for current, latest, desc in cases:
        r = compare_versions(current, latest)
        symbol = {-1: "<", 0: "==", 1: ">"}[r]
        print(f"  v{current} {symbol} v{latest}  ({desc})")


if __name__ == "__main__":
    main()
