#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teams課題ダウンローダー ビルドツール

- バージョン番号の入力・version.py の自動更新
- リリース用ZIPの作成（不要ファイルを除外）
- GitHub Releases用のリリースノート生成
"""

import os
import sys
import re
import zipfile
from datetime import datetime

# パス設定
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(REPO_ROOT, "app")
VERSION_FILE = os.path.join(APP_DIR, "core", "version.py")

# ZIPに含めるファイル（REPO_ROOT相対）
INCLUDE_FILES = [
    "startup_gui.bat",
    "app/main.py",
    "app/startup_gui.ps1",
    "app/config.json",
]

# ZIPに含めるディレクトリ（app/ 配下、再帰的に .py を収集）
INCLUDE_DIRS = [
    "app/core",
    "app/gui",
    "app/models",
    "app/services",
    "app/utils",
]

# 除外パターン
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    "test_write_permission.py",
]


def get_current_version():
    """version.py から現在のバージョンを読み取る"""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'VERSION\s*=\s*"([^"]+)"', content)
    if match:
        return match.group(1)
    return "0.0.0"


def update_version(new_version):
    """version.py のバージョンを更新"""
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r'VERSION\s*=\s*"[^"]+"',
        f'VERSION = "{new_version}"',
        content,
    )

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def should_exclude(path):
    """除外対象かどうか"""
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path:
            return True
    return False


def collect_files():
    """ZIPに含めるファイル一覧を収集"""
    files = []

    # 個別ファイル
    for rel_path in INCLUDE_FILES:
        full_path = os.path.join(REPO_ROOT, rel_path)
        if os.path.exists(full_path):
            files.append((full_path, rel_path))

    # ディレクトリ再帰
    for dir_rel in INCLUDE_DIRS:
        dir_full = os.path.join(REPO_ROOT, dir_rel)
        if not os.path.isdir(dir_full):
            continue
        for root, dirs, filenames in os.walk(dir_full):
            for filename in filenames:
                if not filename.endswith(".py"):
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, REPO_ROOT)
                rel_path = rel_path.replace("\\", "/")
                if not should_exclude(rel_path):
                    files.append((full_path, rel_path))

    return sorted(files, key=lambda x: x[1])


def get_release_dir(version):
    """リリース用ディレクトリを取得・作成"""
    release_dir = os.path.join(REPO_ROOT, "Releases", f"v{version}")
    os.makedirs(release_dir, exist_ok=True)
    return release_dir


def create_zip(version, files):
    """リリース用ZIPを作成"""
    release_dir = get_release_dir(version)
    zip_name = f"TeamsDownloader-v{version}.zip"
    zip_path = os.path.join(release_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full_path, rel_path in files:
            zf.write(full_path, rel_path)

    return zip_path, zip_name


def get_git_log(prev_version=None):
    """前バージョンからのgitログを取得"""
    import subprocess

    try:
        if prev_version:
            cmd = ["git", "log", f"v{prev_version}..HEAD", "--oneline", "--no-decorate"]
        else:
            cmd = ["git", "log", "--oneline", "--no-decorate", "-20"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=REPO_ROOT, encoding="utf-8"
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
    except Exception:
        pass

    return []


def generate_release_notes(version, prev_version):
    """GitHub Releases用のリリースノートを生成"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"## v{version}",
        "",
        f"リリース日: {date_str}",
        "",
        "### 変更内容",
        "",
    ]

    # gitログから変更内容を取得
    commits = get_git_log(prev_version)
    if commits:
        for commit in commits:
            # ハッシュを除去してメッセージのみ
            parts = commit.split(" ", 1)
            msg = parts[1] if len(parts) > 1 else parts[0]
            lines.append(f"- {msg}")
    else:
        lines.append("- （変更内容をここに記載）")

    lines.extend([
        "",
        "### インストール方法",
        "",
        "1. ZIPファイルをダウンロードして展開",
        "2. `startup_gui.bat` をダブルクリックして起動",
        "",
    ])

    return "\n".join(lines)


def main():
    print("=" * 50)
    print("Teams課題ダウンローダー ビルドツール")
    print("=" * 50)

    # 現在のバージョン
    current_version = get_current_version()
    print(f"\n現在のバージョン: v{current_version}")

    # 新バージョン入力
    new_version = input(f"新しいバージョン (Enter でスキップ): ").strip()
    if not new_version:
        new_version = current_version
        print(f"バージョン据え置き: v{new_version}")
    else:
        # バージョン形式チェック
        if not re.match(r"^\d+\.\d+\.\d+$", new_version):
            print("エラー: バージョンは X.Y.Z 形式で入力してください")
            sys.exit(1)

        if new_version != current_version:
            update_version(new_version)
            print(f"バージョンを更新: v{current_version} -> v{new_version}")

    # ファイル収集
    print(f"\nファイルを収集中...")
    files = collect_files()
    print(f"  {len(files)} ファイル")

    for _, rel_path in files:
        print(f"    {rel_path}")

    # ZIP作成
    print(f"\nZIPを作成中...")
    zip_path, zip_name = create_zip(new_version, files)
    zip_size = os.path.getsize(zip_path)
    print(f"  {zip_name} ({zip_size:,} bytes)")

    # リリースノート生成
    print(f"\nリリースノートを生成中...")
    release_notes = generate_release_notes(new_version, current_version if new_version != current_version else None)

    release_dir = get_release_dir(new_version)
    notes_file = os.path.join(release_dir, f"RELEASE_NOTES_v{new_version}.md")
    with open(notes_file, "w", encoding="utf-8") as f:
        f.write(release_notes)
    print(f"  {os.path.basename(notes_file)}")

    # 結果表示
    print(f"\n{'=' * 50}")
    print(f"ビルド完了!")
    print(f"{'=' * 50}")
    print(f"  ZIP:   {zip_path}")
    print(f"  Notes: {notes_file}")
    print(f"\nGitHub Releases で以下を設定:")
    print(f"  Tag:   v{new_version}")
    print(f"  Title: v{new_version}")
    print(f"  Body:  {os.path.basename(notes_file)} の内容を貼り付け")
    print(f"  Asset: {zip_name} を添付")


if __name__ == "__main__":
    main()
