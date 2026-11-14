#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
複数クラス記号を持つ学生の選択ロジック
"""

from typing import Callable, List, Dict, Optional


def _is_code_like(part: str) -> bool:
    """クラス名の断片がクラス記号らしいか判定

    クラス記号は英字と数字の組み合わせ（例: AT51A512）のため、
    「英数字のみ・4文字以上・英字と数字の両方を含む」ものだけを対象にする。
    （MASUDA のような担当者名は前方一致の対象から除外される）
    """
    if len(part) < 4 or not part.isalnum():
        return False
    return any(c.isdigit() for c in part) and any(c.isalpha() for c in part)


def build_class_code_matcher(
    class_name: str,
    known_codes: Optional[List[str]] = None
) -> Callable[[str], bool]:
    """このクラスのクラス記号かどうかを判定する関数を返す

    Teamsのクラス名（例: OHC25-AT51A-GP51A-GC51A）は、名簿のクラス記号
    （例: AT51A512）が途中で切られていることがある。そのため
      1. SharePointスキャンで検出済みのクラス記号（完全一致）
      2. クラス名を '-' で分割した断片（完全一致）
      3. 同じ断片による前方一致（AT51A → AT51A512）
    の順で照合する。

    Args:
        class_name: Teamsのクラス名
        known_codes: キャッシュ済みのクラス記号リスト（cache.get_class_codes）

    Returns:
        クラス記号を受け取って一致可否を返す関数
    """
    codes = {str(c).strip().upper() for c in (known_codes or []) if c}
    parts = {p.strip().upper() for p in class_name.split('-') if p.strip()}
    prefixes = {p for p in parts if _is_code_like(p)}

    def matches(class_code: str) -> bool:
        if not class_code:
            return False
        code = str(class_code).strip().upper()
        if code in codes or code in parts:
            return True
        return any(code.startswith(prefix) for prefix in prefixes)

    return matches


def flatten_students_info(students_info: Dict) -> List[Dict]:
    """名簿の辞書を学生情報のフラットなリストに変換

    複数クラス記号を持つ学生は、クラス記号ごとに1件ずつ展開される。
    """
    students = []
    for info in students_info.values():
        if isinstance(info, list):
            students.extend(info)
        else:
            students.append(info)
    return students


def select_class_code_for_student(
    student_info_list: List[Dict],
    class_name: str,
    cached_selection: Optional[str] = None,
    known_codes: Optional[List[str]] = None
) -> Dict:
    """複数クラス記号を持つ学生から適切なクラス記号を選択

    Args:
        student_info_list: 学生情報のリスト（複数クラス記号）
        class_name: 現在のクラス名
        cached_selection: キャッシュされた選択
        known_codes: キャッシュ済みのクラス記号リスト

    Returns:
        選択された学生情報
    """
    # 1. キャッシュされた選択があればそれを使用
    if cached_selection:
        for item in student_info_list:
            if item.get('class_code') == cached_selection:
                return item

    # 2. クラス名（または検出済みクラス記号）と一致するクラス記号を探す
    matches = build_class_code_matcher(class_name, known_codes)
    for item in student_info_list:
        if matches(item.get('class_code', '')):
            return item

    # 3. デフォルトは最初のクラス記号
    return student_info_list[0]


def get_class_codes_from_students(
    student_info_list: List[Dict],
    class_name: str,
    cached_selection: Optional[str] = None,
    known_codes: Optional[List[str]] = None
) -> str:
    """複数クラス記号を持つ学生リストから適切なクラス記号を取得

    Args:
        student_info_list: 学生情報のリスト（複数クラス記号）
        class_name: 現在のクラス名
        cached_selection: キャッシュされた選択
        known_codes: キャッシュ済みのクラス記号リスト

    Returns:
        選択されたクラス記号
    """
    selected = select_class_code_for_student(
        student_info_list,
        class_name,
        cached_selection,
        known_codes
    )
    return selected.get('class_code', '')


def filter_students_by_class(
    students_info: Dict,
    class_name: str,
    cache_manager,
    known_codes: Optional[List[str]] = None
) -> List[Dict]:
    """クラス名に一致する学生のみをフィルタリング

    Args:
        students_info: 全学生情報
        class_name: クラス名
        cache_manager: キャッシュマネージャー
        known_codes: キャッシュ済みのクラス記号リスト（cache.get_class_codes）

    Returns:
        フィルタリングされた学生リスト
    """
    matches = build_class_code_matcher(class_name, known_codes)
    filtered = []

    for name_key, info in students_info.items():
        if isinstance(info, list):
            # 複数クラス記号を持つ学生の場合
            cached_selection = None
            if cache_manager:
                cached_selection = cache_manager.get_class_code_selection(
                    class_name, info[0].get('student_name')
                )

            selected_info = None

            if cached_selection and matches(cached_selection):
                # 選択履歴があり、このクラスのクラス記号と一致
                selected_info = next(
                    (item for item in info if item.get('class_code') == cached_selection),
                    None
                )

            if selected_info is None:
                # このクラスに一致するクラス記号を探す
                selected_info = next(
                    (item for item in info if matches(item.get('class_code', ''))),
                    None
                )

            if selected_info:
                filtered.append(selected_info)
        else:
            # 単一クラス記号の場合
            if matches(info.get('class_code', '')):
                filtered.append(info)

    return filtered
