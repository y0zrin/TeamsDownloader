#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIダイアログパッケージ

各種ダイアログクラスを提供
"""

from .auth_dialogs import DeviceCodeDialog
from .class_dialogs import ClassCodeSelectionDialog, EditClassDialog
from .student_dialogs import (
    UnsubmittedStudentsDialog,
    SelectStudentsDialog,
    NameMappingDialog
)
from .settings_dialogs import FontSettingsDialog
from .progress_dialogs import ProgressDialog, DownloadCompleteDialog
from .delete_dialogs import DeleteConfirmDialog, DeleteCompleteDialog

__all__ = [
    'DeviceCodeDialog',
    'ClassCodeSelectionDialog',
    'EditClassDialog',
    'UnsubmittedStudentsDialog',
    'SelectStudentsDialog',
    'NameMappingDialog',
    'FontSettingsDialog',
    'ProgressDialog',
    'DownloadCompleteDialog',
    'DeleteConfirmDialog',
    'DeleteCompleteDialog',
]
