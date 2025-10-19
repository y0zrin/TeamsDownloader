#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学生管理関連ダイアログ（リファクタリング版）
"""

import tkinter as tk
from tkinter import ttk, messagebox
from models.student import format_student_display, sort_students
from utils.student_selector import filter_students_by_class
from gui.dialogs.dialog_utils import create_centered_dialog

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class UnsubmittedStudentsDialog:
    """未提出者一覧ダイアログ"""
    def __init__(self, parent, class_name, assignment_name, unsubmitted_list):
        self.dialog = create_centered_dialog(parent, "未提出者一覧", 600, 500)
        
        # タイトル
        title_frame = ttk.Frame(self.dialog, padding="10")
        title_frame.pack(fill=tk.X)
        
        ttk.Label(
            title_frame,
            text=f"📊 未提出者一覧",
            font=("", 14, "bold")
        ).pack()
        
        ttk.Label(
            title_frame,
            text=f"クラス: {class_name} | 課題: {assignment_name}",
            font=("", 10)
        ).pack(pady=5)
        
        ttk.Label(
            title_frame,
            text=f"未提出者: {len(unsubmitted_list)}人",
            foreground="red",
            font=("", 10, "bold")
        ).pack()
        
        # リストフレーム
        list_frame = ttk.Frame(self.dialog, padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # リストボックス
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", 10),
            selectmode=tk.EXTENDED
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # 未提出者をリストに追加（共通関数を使用）
        for student_info in unsubmitted_list:
            display_text = format_student_display(student_info)
            self.listbox.insert(tk.END, display_text)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="📋 コピー",
            command=self._copy_to_clipboard,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="閉じる",
            command=self.dialog.destroy,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _copy_to_clipboard(self):
        """リスト内容をクリップボードにコピー"""
        items = self.listbox.get(0, tk.END)
        text = '\n'.join(items)
        
        try:
            if CLIPBOARD_AVAILABLE:
                import pyperclip
                pyperclip.copy(text)
            else:
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(text)
            
            # 一時的にボタンのテキストを変更
            for widget in self.dialog.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for button in widget.winfo_children():
                        if isinstance(button, ttk.Button) and button.cget('text') == '📋 コピー':
                            button.configure(text='✓ コピー済み')
                            self.dialog.after(2000, lambda: button.configure(text='📋 コピー'))
                            break
        except Exception as e:
            print(f"クリップボードへのコピーエラー: {e}")


class SelectStudentsDialog:
    """特定学生選択ダイアログ（全学生表示版）"""
    def __init__(self, parent, students_info, current_class_name):
        self.selected_students = None
        self.dialog = create_centered_dialog(parent, "ダウンロード対象学生を選択", 500, 620)
        
        # タイトル
        title_frame = ttk.Frame(self.dialog, padding="10")
        title_frame.pack(fill=tk.X)
        
        ttk.Label(
            title_frame,
            text=f"📥 ダウンロード対象学生を選択",
            font=("", 12, "bold")
        ).pack()
        
        ttk.Label(
            title_frame,
            text=f"クラス: {current_class_name}",
            font=("", 10),
            foreground="blue"
        ).pack(pady=5)
        
        ttk.Label(
            title_frame,
            text="複数選択可能です。Ctrlキーを押しながらクリックしてください。",
            font=("", 9),
            foreground="gray"
        ).pack()
        
        # 検索バー
        search_frame = ttk.Frame(self.dialog, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="🔍 検索:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var.trace('w', self._filter_list)
        self.search_entry.focus()
        
        # 学生リスト
        list_frame = ttk.Frame(self.dialog, padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", 10),
            selectmode=tk.EXTENDED
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # 学生データをフィルタリングしてソート（共通関数を使用）
        from core.cache import AssignmentCache
        cache = AssignmentCache()
        
        self.all_students = filter_students_by_class(
            students_info, current_class_name, cache
        )
        self.all_students = sort_students(self.all_students)
        
        self._populate_list()
        
        # 選択状況表示
        status_frame = ttk.Frame(self.dialog, padding="5")
        status_frame.pack(fill=tk.X)
        
        self.count_label = ttk.Label(
            status_frame,
            text="0人選択中",
            font=("", 9),
            foreground="gray"
        )
        self.count_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            status_frame,
            text="全選択",
            command=self._select_all,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            status_frame,
            text="選択解除",
            command=self._deselect_all,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.dialog, padding="15")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # 選択変更イベント
        self.listbox.bind('<<ListboxSelect>>', self._on_selection_changed)
    
    def _populate_list(self, students=None):
        """リストを更新（共通関数を使用）"""
        self.listbox.delete(0, tk.END)
        
        if students is None:
            students = self.all_students
        
        for student_info in students:
            display_text = format_student_display(student_info)
            self.listbox.insert(tk.END, display_text)
    
    def _filter_list(self, *args):
        """検索フィルタ"""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            self._populate_list()
            return
        
        filtered = [s for s in self.all_students 
                   if search_text in s.get('student_name', '').lower() or
                      search_text in s.get('class_code', '').lower() or
                      search_text in str(s.get('attendance_number', '')).lower()]
        
        self._populate_list(filtered)
    
    def _select_all(self):
        """全選択"""
        self.listbox.select_set(0, tk.END)
        self._on_selection_changed()
    
    def _deselect_all(self):
        """選択解除"""
        self.listbox.selection_clear(0, tk.END)
        self._on_selection_changed()
    
    def _on_selection_changed(self, event=None):
        """選択変更時"""
        count = len(self.listbox.curselection())
        self.count_label.config(text=f"{count}人選択中")
    
    def _on_ok(self):
        """OK押下"""
        selected_indices = self.listbox.curselection()
        
        if not selected_indices:
            self.selected_students = None
        else:
            self.selected_students = []
            for idx in selected_indices:
                if idx < len(self.all_students):
                    student_info = self.all_students[idx]
                    self.selected_students.append({
                        'class_code': student_info.get('class_code'),
                        'attendance_number': student_info.get('attendance_number'),
                        'student_name': student_info.get('student_name')
                    })
        
        self.dialog.destroy()
    
    def _on_cancel(self):
        """キャンセル押下"""
        self.selected_students = None
        self.dialog.destroy()
    
    def show(self):
        """ダイアログを表示して結果を返す"""
        self.dialog.wait_window()
        return self.selected_students


class NameMappingDialog:
    """SharePoint名と名簿名の紐付けダイアログ"""
    def __init__(self, parent, sharepoint_name, students_info):
        self.selected_student = None
        self.dialog = create_centered_dialog(parent, "学生名の紐付け", 600, 550)
        
        # タイトル
        title_frame = ttk.Frame(self.dialog, padding="15")
        title_frame.pack(fill=tk.X)
        
        ttk.Label(
            title_frame,
            text="📝 名簿に見つかりません",
            font=("", 13, "bold")
        ).pack()
        
        ttk.Label(
            title_frame,
            text=f"SharePoint: {sharepoint_name}",
            font=("", 11),
            foreground="blue"
        ).pack(pady=5)
        
        ttk.Label(
            title_frame,
            text="この学生は名簿のどの学生と一致しますか？",
            font=("", 10)
        ).pack(pady=5)
        
        # 説明
        info_frame = ttk.Frame(self.dialog, padding="10")
        info_frame.pack(fill=tk.X)
        
        ttk.Label(
            info_frame,
            text="💡 設定は保存され、次回以降は自動で紐付けられます",
            font=("", 9),
            foreground="gray"
        ).pack()
        
        # 検索バー
        search_frame = ttk.Frame(self.dialog, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="🔍 検索:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var.trace('w', self._filter_list)
        self.search_entry.focus()
        
        # 学生リスト
        list_frame = ttk.Frame(self.dialog, padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("", 10),
            activestyle='dotbox'
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # ダブルクリックで選択
        self.listbox.bind('<Double-Button-1>', lambda e: self._on_select())
        
        # 学生データを準備してソート（共通関数を使用）
        self.all_students = []
        for name_key, info in students_info.items():
            if isinstance(info, list):
                # 複数クラスの場合は全て追加
                for item in info:
                    self.all_students.append(item)
            else:
                self.all_students.append(info)
        
        self.all_students = sort_students(self.all_students)
        
        self._populate_list()
        
        # ボタン
        button_frame = ttk.Frame(self.dialog, padding="15")
        button_frame.pack(fill=tk.X)
        
        btn_frame1 = ttk.Frame(button_frame)
        btn_frame1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            btn_frame1,
            text="✅ この学生と紐付ける",
            command=self._on_select,
            width=25
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        ttk.Button(
            btn_frame1,
            text="⏭️ 今回はスキップ",
            command=self._on_skip,
            width=25
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        btn_frame2 = ttk.Frame(button_frame)
        btn_frame2.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame2,
            text="❌ 除外する（退学者等）",
            command=self._on_exclude,
            width=25
        ).pack(expand=True, fill=tk.X)
    
    def _populate_list(self, students=None):
        """リストを更新（共通関数を使用）"""
        self.listbox.delete(0, tk.END)
        if students is None:
            students = self.all_students
        
        for student in students:
            display = format_student_display(student)
            self.listbox.insert(tk.END, display)
    
    def _filter_list(self, *args):
        """検索フィルタ"""
        search = self.search_var.get().lower()
        if not search:
            self._populate_list()
            return
        
        filtered = [s for s in self.all_students 
                   if search in s.get('student_name', '').lower() or
                      search in s.get('class_code', '').lower() or
                      search in str(s.get('attendance_number', '')).lower()]
        
        self._populate_list(filtered)
    
    def _get_selected_student(self):
        """選択された学生を取得"""
        selection = self.listbox.curselection()
        if not selection:
            return None
        
        idx = selection[0]
        # フィルタされたリストから該当学生を取得
        search = self.search_var.get().lower()
        if search:
            filtered = [s for s in self.all_students 
                       if search in s.get('student_name', '').lower() or
                          search in s.get('class_code', '').lower() or
                          search in str(s.get('attendance_number', '')).lower()]
            return filtered[idx] if idx < len(filtered) else None
        else:
            return self.all_students[idx] if idx < len(self.all_students) else None
    
    def _on_select(self):
        """選択ボタン"""
        student = self._get_selected_student()
        if not student:
            messagebox.showwarning("警告", "学生を選択してください")
            return
        
        self.selected_student = student
        self.dialog.destroy()
    
    def _on_exclude(self):
        """除外ボタン"""
        if messagebox.askyesno(
            "確認",
            "この学生を除外リストに追加しますか？\n\n"
            "除外された学生は今後のダウンロードで自動的にスキップされます。"
        ):
            self.selected_student = "EXCLUDED"
            self.dialog.destroy()
    
    def _on_skip(self):
        """スキップボタン"""
        self.selected_student = None
        self.dialog.destroy()
    
    def show(self):
        """ダイアログを表示して結果を返す"""
        self.dialog.wait_window()
        return self.selected_student
