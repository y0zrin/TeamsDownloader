#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUIダイアログ群
"""

import tkinter as tk
from tkinter import ttk
import webbrowser
import os

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False


class DeviceCodeDialog:
    """デバイスコード認証用のダイアログ"""
    def __init__(self, parent, user_code, verification_uri):
        self.result = False
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Microsoft認証")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (300 // 2)
        self.dialog.geometry(f"500x300+{x}+{y}")
        
        # タイトル
        title_label = ttk.Label(
            self.dialog, 
            text="🔐 Microsoft認証が必要です",
            font=("", 14, "bold")
        )
        title_label.pack(pady=20)
        
        # 説明
        info_text = "ブラウザが開きますので、以下のコードを入力してください:"
        info_label = ttk.Label(self.dialog, text=info_text)
        info_label.pack(pady=5)
        
        # コード表示エリア
        code_frame = ttk.Frame(self.dialog)
        code_frame.pack(pady=10, padx=20, fill=tk.X)
        
        self.code_entry = ttk.Entry(
            code_frame,
            font=("Courier", 16, "bold"),
            justify=tk.CENTER
        )
        self.code_entry.pack(fill=tk.X, pady=5)
        self.code_entry.insert(0, user_code)
        self.code_entry.configure(state='readonly')
        
        # 自動的にクリップボードにコピー
        try:
            if CLIPBOARD_AVAILABLE:
                import pyperclip
                pyperclip.copy(user_code)
            else:
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(user_code)
        except:
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(user_code)
        
        # コピー済みメッセージ
        copied_label = ttk.Label(
            code_frame,
            text="✓ クリップボードにコピー済み",
            foreground="green"
        )
        copied_label.pack(pady=5)
        
        # URLとボタン
        url_frame = ttk.Frame(self.dialog)
        url_frame.pack(pady=10)
        
        url_label = ttk.Label(url_frame, text=verification_uri, foreground="blue", cursor="hand2")
        url_label.pack()
        url_label.bind("<Button-1>", lambda e: webbrowser.open(verification_uri))
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        open_browser_btn = ttk.Button(
            button_frame,
            text="🌐 ブラウザで開く",
            command=lambda: webbrowser.open(verification_uri)
        )
        open_browser_btn.pack(side=tk.LEFT, padx=5)
        
        # 自動的にブラウザを開く
        try:
            webbrowser.open(verification_uri)
        except:
            pass
        
        # 認証待ちメッセージ
        wait_label = ttk.Label(
            self.dialog,
            text="認証完了を待っています...",
            foreground="gray"
        )
        wait_label.pack(pady=10)
    
    def close(self):
        self.dialog.destroy()


class ClassCodeSelectionDialog:
    """クラス記号選択ダイアログ"""
    def __init__(self, parent, student_name, class_codes, current_class):
        self.selected_code = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("クラス記号を選択")
        self.dialog.geometry("450x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 225
        y = (self.dialog.winfo_screenheight() // 2) - 150
        self.dialog.geometry(f"450x300+{x}+{y}")
        
        # 説明
        info_frame = ttk.Frame(self.dialog, padding="20")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            info_frame,
            text=f"学生: {student_name}",
            font=("", 11, "bold")
        ).pack(pady=(0, 5))
        
        ttk.Label(
            info_frame,
            text=f"現在のクラス: {current_class}",
            foreground="blue"
        ).pack(pady=(0, 10))
        
        ttk.Label(
            info_frame,
            text="複数のクラス記号があります。\n使用するクラス記号を選択してください:",
            justify=tk.LEFT
        ).pack(pady=(0, 10))
        
        # ラジオボタン
        self.selected_var = tk.StringVar()
        
        # 推奨を最初に設定
        recommended = None
        for code in class_codes:
            if self._is_similar(code, current_class):
                recommended = code
                break
        
        if recommended:
            self.selected_var.set(recommended)
        else:
            self.selected_var.set(class_codes[0])
        
        for code in class_codes:
            # 推奨マークを表示
            if self._is_similar(code, current_class):
                label_text = f"{code} (推奨)"
            else:
                label_text = code
            
            rb = ttk.Radiobutton(
                info_frame,
                text=label_text,
                value=code,
                variable=self.selected_var
            )
            rb.pack(anchor=tk.W, pady=2)
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="キャンセル",
            command=self._on_skip,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _is_similar(self, code, class_name):
        """クラス記号がクラス名と類似しているか"""
        class_code = class_name.split('-')[-1] if '-' in class_name else class_name
        common_prefix = os.path.commonprefix([code, class_code])
        return len(common_prefix) >= 4  # 4文字以上一致
    
    def _on_ok(self):
        self.selected_code = self.selected_var.get()
        self.dialog.destroy()
    
    def _on_skip(self):
        self.selected_code = None
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.selected_code


# ========== 新機能1: クラス編集ダイアログ ==========

class EditClassDialog:
    """クラス編集ダイアログ"""
    def __init__(self, parent, current_name):
        self.new_name = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("クラス編集")
        self.dialog.geometry("380x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 190
        y = (self.dialog.winfo_screenheight() // 2) - 100
        self.dialog.geometry(f"380x200+{x}+{y}")
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 説明
        ttk.Label(
            main_frame,
            text=f"現在のクラス名: {current_name}",
            font=("", 10, "bold")
        ).pack(pady=(0, 10))
        
        ttk.Label(
            main_frame,
            text="新しいクラス名を入力してください:"
        ).pack(pady=(0, 5))
        
        # 入力欄
        self.entry = ttk.Entry(main_frame, width=35)
        self.entry.pack(pady=5)
        self.entry.insert(0, current_name)
        self.entry.focus()
        self.entry.select_range(0, tk.END)
        
        # Enterキーでも確定
        self.entry.bind('<Return>', lambda e: self._on_ok())
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
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
    
    def _on_ok(self):
        self.new_name = self.entry.get().strip()
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.new_name = None
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.new_name


# ========== 新機能4: 未提出者一覧ダイアログ ==========

class UnsubmittedStudentsDialog:
    """未提出者一覧ダイアログ"""
    def __init__(self, parent, class_name, assignment_name, unsubmitted_list):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("未提出者一覧")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 300
        y = (self.dialog.winfo_screenheight() // 2) - 250
        self.dialog.geometry(f"600x500+{x}+{y}")
        
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
        
        # 未提出者をリストに追加
        for student_info in unsubmitted_list:
            class_code = student_info.get('class_code', '')
            attendance_num = student_info.get('attendance_number', '')
            name = student_info.get('student_name', student_info.get('name', ''))
            
            try:
                num_str = f"{int(attendance_num):02d}"
            except:
                num_str = str(attendance_num)
            
            display_text = f"[{class_code}] {num_str} {name}"
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


# ========== 新機能5: 特定学生選択ダイアログ（クラスフィルタリング対応版）==========

class SelectStudentsDialog:
    """特定学生選択ダイアログ（クラスフィルタリング＋clean_student_name対応版）"""
    def __init__(self, parent, students_info, current_class_name):
        self.selected_students = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("ダウンロード対象学生を選択")
        self.dialog.geometry("500x620")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 310
        self.dialog.geometry(f"500x620+{x}+{y}")
        
        # タイトル
        title_frame = ttk.Frame(self.dialog, padding="10")
        title_frame.pack(fill=tk.X)
        
        ttk.Label(
            title_frame,
            text=f"📥 ダウンロード対象学生を選択 - {current_class_name}",
            font=("", 12, "bold")
        ).pack()
        
        ttk.Label(
            title_frame,
            text="Ctrl/Shiftキーで複数選択できます",
            font=("", 9),
            foreground="gray"
        ).pack(pady=5)
        
        # 検索バー
        search_frame = ttk.Frame(self.dialog, padding="10")
        search_frame.pack(fill=tk.X)
        
        ttk.Label(search_frame, text="🔍").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var.trace('w', self._filter_list)
        
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
        
        # クラス名からクラスコードを抽出
        if '-' in current_class_name:
            target_class_code = current_class_name.split('-')[-1]
        else:
            target_class_code = current_class_name
        
        # 学生情報を格納（現在のクラスのみ）
        self.all_students = []
        
        # 学生情報からリストを作成（クラスフィルタリング）
        if students_info:
            for name_key, info in students_info.items():
                if isinstance(info, list):
                    # 複数クラス記号を持つ学生
                    for student_info in info:
                        student_class_code = student_info.get('class_code', '')
                        # 完全一致または前方一致（柔軟性を持たせる）
                        if (student_class_code == target_class_code or 
                            student_class_code.startswith(target_class_code[:6])):
                            self.all_students.append(student_info)
                            break
                else:
                    student_class_code = info.get('class_code', '')
                    # 完全一致または前方一致
                    if (student_class_code == target_class_code or 
                        student_class_code.startswith(target_class_code[:6])):
                        self.all_students.append(info)
            
            # ソート
            self.all_students.sort(key=lambda x: (x.get('class_code', ''), int(x.get('attendance_number', 0)) if x.get('attendance_number', '').isdigit() else 999))
        
        # リストに追加
        self._populate_list()
        
        # 選択ボタン
        selection_frame = ttk.Frame(self.dialog, padding="5")
        selection_frame.pack(fill=tk.X)
        
        ttk.Button(
            selection_frame,
            text="全選択",
            command=self._select_all,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            selection_frame,
            text="選択解除",
            command=self._deselect_all,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        # 確認ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        self.count_label = ttk.Label(
            button_frame,
            text="0人選択中",
            font=("", 9),
            foreground="blue"
        )
        self.count_label.pack(side=tk.LEFT, padx=10)
        
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
        """リストを更新"""
        self.listbox.delete(0, tk.END)
        
        if students is None:
            students = self.all_students
        
        for student_info in students:
            class_code = student_info.get('class_code', '')
            attendance_num = student_info.get('attendance_number', '')
            name = student_info.get('student_name', student_info.get('name', ''))
            
            try:
                num_str = f"{int(attendance_num):02d}"
            except:
                num_str = str(attendance_num)
            
            display_text = f"[{class_code}] {num_str} {name}"
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
                # 現在表示されているリストから該当する学生情報を取得
                display_text = self.listbox.get(idx)
                
                # 表示テキストから学生情報を逆引き
                for student_info in self.all_students:
                    class_code = student_info.get('class_code', '')
                    attendance_num = student_info.get('attendance_number', '')
                    name = student_info.get('student_name', student_info.get('name', ''))
                    
                    try:
                        num_str = f"{int(attendance_num):02d}"
                    except:
                        num_str = str(attendance_num)
                    
                    expected_text = f"[{class_code}] {num_str} {name}"
                    
                    if expected_text == display_text:
                        # clean_student_name相当の処理を適用した名前を返す
                        from utils.file_utils import clean_student_name
                        cleaned_name = clean_student_name(name)
                        self.selected_students.append(cleaned_name)
                        break
        
        self.dialog.destroy()
    
    def _on_cancel(self):
        """キャンセル押下"""
        self.selected_students = None
        self.dialog.destroy()
    
    def show(self):
        """ダイアログを表示して結果を返す"""
        self.dialog.wait_window()
        return self.selected_students


# ========== 新機能2: フォント設定ダイアログ ==========

class FontSettingsDialog:
    """フォント設定ダイアログ"""
    def __init__(self, parent, current_size):
        self.selected_size = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("フォント設定")
        self.dialog.geometry("380x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 190
        y = (self.dialog.winfo_screenheight() // 2) - 175
        self.dialog.geometry(f"380x350+{x}+{y}")
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        ttk.Label(
            main_frame,
            text="🔤 フォントサイズ設定",
            font=("", 12, "bold")
        ).pack(pady=(0, 15))
        
        ttk.Label(
            main_frame,
            text="フォントサイズを選択してください:",
            font=("", 10)
        ).pack(pady=(0, 10))
        
        # ラジオボタンフレーム
        radio_frame = ttk.Frame(main_frame)
        radio_frame.pack(fill=tk.BOTH, expand=True)
        
        # ラジオボタン
        self.size_var = tk.StringVar(value=current_size)
        
        size_options = [
            ('smallest', '最小 (8pt)'),
            ('small', '小 (9pt) - デフォルト'),
            ('medium', '中 (10pt)'),
            ('large', '大 (11pt)'),
            ('largest', '最大 (12pt)'),
        ]
        
        for value, label in size_options:
            ttk.Radiobutton(
                radio_frame,
                text=label,
                value=value,
                variable=self.size_var
            ).pack(anchor=tk.W, padx=20, pady=5)
        
        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)
        
        ttk.Button(
            button_frame,
            text="適用",
            command=self._on_ok,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=12
        ).pack(side=tk.LEFT, padx=5)
    
    def _on_ok(self):
        self.selected_size = self.size_var.get()
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.selected_size = None
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.selected_size


# ========== プログレスバーダイアログ ==========

class ProgressDialog:
    """プログレスバー表示ダイアログ（モーダル）"""
    def __init__(self, parent, title="処理中", message="処理を実行しています..."):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.protocol("WM_DELETE_WINDOW", lambda: None)  # 閉じるボタンを無効化
        
        # センタリング
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 250
        y = (self.dialog.winfo_screenheight() // 2) - 100
        self.dialog.geometry(f"500x200+{x}+{y}")
        
        # メインフレーム
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトルラベル
        self.title_label = ttk.Label(
            main_frame,
            text=title,
            font=("", 12, "bold")
        )
        self.title_label.pack(pady=(0, 15))
        
        # メッセージラベル
        self.message_label = ttk.Label(
            main_frame,
            text=message,
            font=("", 10)
        )
        self.message_label.pack(pady=(0, 10))
        
        # プログレスバー（不確定モード）
        self.progress = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=400
        )
        self.progress.pack(pady=(0, 10))
        self.progress.start(10)  # アニメーション開始
        
        # 詳細メッセージラベル
        self.detail_label = ttk.Label(
            main_frame,
            text="",
            font=("", 9),
            foreground="gray"
        )
        self.detail_label.pack(pady=(10, 0))
        
        # ダイアログを更新
        self.dialog.update()
    
    def update_message(self, message):
        """メッセージを更新"""
        self.message_label.config(text=message)
        self.dialog.update()
    
    def update_detail(self, detail):
        """詳細メッセージを更新"""
        self.detail_label.config(text=detail)
        self.dialog.update()
    
    def close(self):
        """ダイアログを閉じる"""
        try:
            self.progress.stop()
            self.dialog.destroy()
        except:
            pass
