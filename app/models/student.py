#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学生情報ドメインモデル
"""

from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class Student:
    """学生情報"""
    student_name: str
    class_code: str
    attendance_number: str
    name_key: str  # スペースを除去した正規化名
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Student':
        """辞書から学生情報を作成"""
        return cls(
            student_name=data.get('student_name', ''),
            class_code=data.get('class_code', ''),
            attendance_number=str(data.get('attendance_number', '')),
            name_key=data.get('name_key', '')
        )
    
    def to_dict(self) -> dict:
        """辞書に変換"""
        return {
            'student_name': self.student_name,
            'class_code': self.class_code,
            'attendance_number': self.attendance_number,
            'name_key': self.name_key
        }
    
    @property
    def formatted_attendance_number(self) -> str:
        """ゼロ埋めされた出席番号を取得"""
        try:
            return f"{int(self.attendance_number):02d}"
        except (ValueError, TypeError):
            return str(self.attendance_number)
    
    @property
    def folder_name(self) -> str:
        """フォルダ名を取得（出席番号_氏名）"""
        return f"{self.formatted_attendance_number}_{self.student_name}"
    
    def get_display_text(self) -> str:
        """表示用テキストを取得（[クラス記号] 出席番号 氏名）"""
        return f"[{self.class_code}] {self.formatted_attendance_number} {self.student_name}"
    
    def __str__(self) -> str:
        return self.get_display_text()


def format_student_display(student_dict: dict) -> str:
    """辞書形式の学生情報から表示用テキストを生成
    
    Args:
        student_dict: 学生情報辞書 (class_code, attendance_number, student_name or name)
    
    Returns:
        表示用テキスト
    """
    class_code = student_dict.get('class_code', '')
    attendance_num = student_dict.get('attendance_number', '')
    name = student_dict.get('student_name', student_dict.get('name', ''))
    
    try:
        num_str = f"{int(attendance_num):02d}"
    except (ValueError, TypeError):
        num_str = str(attendance_num)
    
    return f"[{class_code}] {num_str} {name}"


def sort_students(students: List[dict]) -> List[dict]:
    """学生リストをクラス記号・出席番号順にソート
    
    Args:
        students: 学生情報辞書のリスト
    
    Returns:
        ソート済みの学生リスト
    """
    return sorted(students, key=lambda x: (
        x.get('class_code', ''),
        int(x.get('attendance_number', 0)) 
        if str(x.get('attendance_number', '')).isdigit() 
        else 999
    ))


@dataclass
class SharePointStudent:
    """SharePoint上の学生フォルダ情報"""
    folder_id: str
    folder_name: str
    current_name: str  # 現在の名前
    
    @property
    def cleaned_name(self) -> str:
        """プレフィックスを除去した名前を取得"""
        from utils.file_utils import clean_student_name
        return clean_student_name(self.folder_name)
    
    @property
    def name_key(self) -> str:
        """スペースを除去した正規化名キーを取得"""
        return self.cleaned_name.replace(' ', '').replace('　', '').strip()


@dataclass
class StudentMapping:
    """学生マッピング情報（IDベース）"""
    folder_id: str
    status: str  # 'MAPPED' or 'EXCLUDED'
    last_known_name: str
    mapped_student: Optional[Student] = None
    mapped_at: Optional[str] = None
    excluded_at: Optional[str] = None
    
    @classmethod
    def from_cache(cls, folder_id: str, cache_data: dict) -> Optional['StudentMapping']:
        """キャッシュから復元"""
        if not cache_data:
            return None
        
        status = cache_data.get('status')
        if status == 'EXCLUDED':
            return cls(
                folder_id=folder_id,
                status='EXCLUDED',
                last_known_name=cache_data.get('last_known_name', ''),
                excluded_at=cache_data.get('excluded_at')
            )
        elif status == 'MAPPED':
            student = Student(
                student_name=cache_data.get('student_name', ''),
                class_code=cache_data.get('class_code', ''),
                attendance_number=cache_data.get('attendance_number', ''),
                name_key=''
            )
            return cls(
                folder_id=folder_id,
                status='MAPPED',
                last_known_name=cache_data.get('last_known_name', ''),
                mapped_student=student,
                mapped_at=cache_data.get('mapped_at')
            )
        return None
    
    @property
    def is_excluded(self) -> bool:
        return self.status == 'EXCLUDED'
    
    @property
    def is_mapped(self) -> bool:
        return self.status == 'MAPPED'
