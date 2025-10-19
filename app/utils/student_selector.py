#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
複数クラス記号を持つ学生の選択ロジック
"""

from typing import List, Dict, Optional


def select_class_code_for_student(
    student_info_list: List[Dict],
    class_name: str,
    cached_selection: Optional[str] = None
) -> Dict:
    """複数クラス記号を持つ学生から適切なクラス記号を選択
    
    Args:
        student_info_list: 学生情報のリスト（複数クラス記号）
        class_name: 現在のクラス名
        cached_selection: キャッシュされた選択
    
    Returns:
        選択された学生情報
    """
    # 1. キャッシュされた選択があればそれを使用
    if cached_selection:
        for item in student_info_list:
            if item.get('class_code') == cached_selection:
                return item
    
    # 2. クラス名と一致するクラス記号を探す
    class_name_parts = set(class_name.split('-'))
    for item in student_info_list:
        code = item.get('class_code', '')
        if code in class_name_parts:
            return item
    
    # 3. デフォルトは最初のクラス記号
    return student_info_list[0]


def get_class_codes_from_students(
    student_info_list: List[Dict],
    class_name: str,
    cached_selection: Optional[str] = None
) -> str:
    """複数クラス記号を持つ学生リストから適切なクラス記号を取得
    
    Args:
        student_info_list: 学生情報のリスト（複数クラス記号）
        class_name: 現在のクラス名
        cached_selection: キャッシュされた選択
    
    Returns:
        選択されたクラス記号
    """
    selected = select_class_code_for_student(
        student_info_list,
        class_name,
        cached_selection
    )
    return selected.get('class_code', '')


def filter_students_by_class(
    students_info: Dict,
    class_name: str,
    cache_manager
) -> List[Dict]:
    """クラス名に一致する学生のみをフィルタリング
    
    Args:
        students_info: 全学生情報
        class_name: クラス名
        cache_manager: キャッシュマネージャー
    
    Returns:
        フィルタリングされた学生リスト
    """
    class_name_parts = set(class_name.split('-'))
    filtered = []
    
    for name_key, info in students_info.items():
        if isinstance(info, list):
            # 複数クラス記号を持つ学生の場合
            cached_selection = cache_manager.get_class_code_selection(
                class_name, info[0].get('student_name')
            )
            
            if cached_selection and cached_selection in class_name_parts:
                # 選択履歴があり、クラス名に一致
                selected_info = next(
                    (item for item in info if item.get('class_code') == cached_selection),
                    None
                )
                if selected_info:
                    filtered.append(selected_info)
            else:
                # クラス名と一致するクラス記号を探す
                for item in info:
                    code = item.get('class_code', '')
                    if code in class_name_parts:
                        filtered.append(item)
                        break
        else:
            # 単一クラス記号の場合
            code = info.get('class_code', '')
            if code in class_name_parts:
                filtered.append(info)
    
    return filtered
