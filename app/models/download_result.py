#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ダウンロード結果ドメインモデル
"""

from dataclasses import dataclass, field
from typing import List, Optional
from models.student import Student


@dataclass
class DownloadedFile:
    """ダウンロードされたファイル情報"""
    file_name: str
    file_path: str
    success: bool
    error: Optional[str] = None


@dataclass
class StudentDownloadResult:
    """学生ごとのダウンロード結果"""
    sharepoint_name: str
    student_info: Optional[Student]
    files: List[DownloadedFile] = field(default_factory=list)
    folder_path: str = ""
    
    @property
    def file_count(self) -> int:
        return len([f for f in self.files if f.success])
    
    @property
    def has_errors(self) -> bool:
        return any(not f.success for f in self.files)
    
    @property
    def display_name(self) -> str:
        """表示用の名前を取得"""
        if self.student_info:
            return str(self.student_info)
        return self.sharepoint_name


@dataclass
class DownloadResult:
    """全体のダウンロード結果"""
    student_count: int
    file_count: int
    folder_path: str
    students: List[StudentDownloadResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    cancelled: bool = False
    
    @property
    def success_rate(self) -> float:
        """成功率を計算"""
        if self.student_count == 0:
            return 0.0
        success_count = len([s for s in self.students if not s.has_errors])
        return (success_count / self.student_count) * 100
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0 or any(s.has_errors for s in self.students)
    
    def add_error(self, error: str):
        """エラーを追加"""
        self.errors.append(error)
    
    def add_student_result(self, result: StudentDownloadResult):
        """学生結果を追加"""
        self.students.append(result)


@dataclass
class UnsubmittedStudent:
    """未提出学生情報"""
    student_info: Student
    
    @property
    def display_text(self) -> str:
        """表示用テキストを取得"""
        return str(self.student_info)


@dataclass
class UnsubmittedCheckResult:
    """未提出確認結果"""
    assignment_name: str
    class_name: str
    total_students: int
    submitted_count: int
    unsubmitted: List[UnsubmittedStudent] = field(default_factory=list)
    error: Optional[str] = None
    
    @property
    def unsubmitted_count(self) -> int:
        return len(self.unsubmitted)
    
    @property
    def submission_rate(self) -> float:
        """提出率を計算"""
        if self.total_students == 0:
            return 0.0
        return (self.submitted_count / self.total_students) * 100
