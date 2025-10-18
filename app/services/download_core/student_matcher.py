#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学生名の照合とマッピング
"""

from typing import Optional, Callable, Dict, List
from models.student import Student, SharePointStudent, StudentMapping
from utils.exceptions import StudentNotFoundError


class StudentMatcher:
    """学生照合クラス"""
    
    def __init__(self, cache_manager, students_info: Dict):
        self.cache = cache_manager
        self.students_info = students_info
        self.multi_class_students = cache_manager.get_multi_class_students()
    
    def match_student(
        self,
        sharepoint_student: SharePointStudent,
        class_name: str,
        class_code_dialog_callback: Optional[Callable] = None
    ) -> Optional[Student]:
        """SharePoint上の学生を名簿と照合
        
        Args:
            sharepoint_student: SharePoint上の学生情報
            class_name: クラス名
            class_code_dialog_callback: クラス記号選択ダイアログのコールバック
        
        Returns:
            照合された学生情報（見つからない場合はNone）
        """
        if not self.students_info:
            return None
        
        # 1. IDベースマッピングをチェック
        cached_mapping = self._check_id_mapping(sharepoint_student.folder_id)
        if cached_mapping:
            if cached_mapping.is_excluded:
                return None
            if cached_mapping.is_mapped:
                return cached_mapping.mapped_student
        
        # 2. 名前で照合
        name_key = sharepoint_student.name_key
        if name_key not in self.students_info:
            return None
        
        # 3. 単一/複数クラス記号の処理
        matched = self.students_info[name_key]
        
        if isinstance(matched, list):
            # 複数クラス記号を持つ学生
            return self._handle_multi_class_student(
                matched, sharepoint_student.folder_name, class_name, class_code_dialog_callback
            )
        else:
            # 単一クラス記号
            return Student.from_dict(matched)
    
    def _check_id_mapping(self, folder_id: str) -> Optional[StudentMapping]:
        """IDベースマッピングをチェック"""
        cache_data = self.cache.get_name_mapping_by_id(folder_id)
        if not cache_data:
            return None
        
        return StudentMapping.from_cache(folder_id, cache_data)
    
    def _handle_multi_class_student(
        self,
        matched_list: List[Dict],
        student_name: str,
        class_name: str,
        class_code_dialog_callback: Optional[Callable]
    ) -> Optional[Student]:
        """複数クラス記号を持つ学生の処理"""
        codes = [s['class_code'] for s in matched_list]
        
        # キャッシュされた選択を確認
        cached_selection = self.cache.get_class_code_selection(class_name, student_name)
        
        if cached_selection:
            # キャッシュから復元
            student_dict = next(
                (s for s in matched_list if s['class_code'] == cached_selection),
                matched_list[0]
            )
            return Student.from_dict(student_dict)
        
        # ダイアログで選択
        if class_code_dialog_callback:
            selected_code = class_code_dialog_callback(student_name, codes, class_name)
            
            if selected_code:
                student_dict = next(
                    (s for s in matched_list if s['class_code'] == selected_code),
                    matched_list[0]
                )
                # 選択を保存
                self.cache.set_class_code_selection(class_name, student_name, selected_code)
                return Student.from_dict(student_dict)
        
        # デフォルトは最初のクラス記号
        return Student.from_dict(matched_list[0])
    
    def save_mapping(self, folder_id: str, folder_name: str, student: Optional[Student] = None):
        """マッピングを保存"""
        if student is None:
            # 除外として保存
            self.cache.set_name_mapping_by_id(folder_id, folder_name, "EXCLUDED")
        else:
            # マッピングとして保存
            self.cache.set_name_mapping_by_id(folder_id, folder_name, student.to_dict())
    
    def is_excluded(self, folder_id: str) -> bool:
        """除外されているかチェック"""
        return self.cache.is_excluded_by_id(folder_id)
    
    def find_student_by_mapping(self, mapping: StudentMapping) -> Optional[Student]:
        """マッピング情報から学生を検索"""
        if not mapping.mapped_student:
            return None
        
        target_class = mapping.mapped_student.class_code
        target_number = mapping.mapped_student.attendance_number
        
        for name_key, info in self.students_info.items():
            if isinstance(info, list):
                for item in info:
                    if (item.get('class_code') == target_class and
                        str(item.get('attendance_number')) == str(target_number)):
                        return Student.from_dict(item)
            else:
                if (info.get('class_code') == target_class and
                    str(info.get('attendance_number')) == str(target_number)):
                    return Student.from_dict(info)
        
        return None
