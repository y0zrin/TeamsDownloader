#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
削除結果ドメインモデル
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StudentDeleteResult:
    """学生ごとの削除結果"""
    student_name: str
    success: bool
    error: Optional[str] = None


@dataclass
class DeleteResult:
    """全体の削除結果"""
    assignment_name: str
    total_students: int = 0
    success_count: int = 0
    fail_count: int = 0
    skip_count: int = 0
    results: List[StudentDeleteResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def has_errors(self) -> bool:
        return self.fail_count > 0

    def add_result(self, result: StudentDeleteResult):
        """結果を追加"""
        self.results.append(result)
        if result.success:
            self.success_count += 1
        else:
            self.fail_count += 1
