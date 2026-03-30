#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
削除関連ダイアログ
"""

import tkinter as tk
from tkinter import ttk
from gui.dialogs.dialog_utils import create_centered_dialog


class DeleteConfirmDialog:
    """削除確認ダイアログ（課題名入力必須）"""

    def __init__(self, parent, class_name, assignment_name):
        """
        Args:
            parent: 親ウィンドウ
            class_name: クラス名
            assignment_name: 削除対象の課題名
        """
        self.confirmed = False
        self.assignment_name = assignment_name
        self.dialog = create_centered_dialog(parent, "課題の削除", 480, 340)

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 警告タイトル
        ttk.Label(
            main_frame,
            text="SharePointから課題を削除します",
            font=("", 12, "bold"),
            foreground="red",
        ).pack(pady=(0, 10))

        # 説明
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="クラス:", font=("", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=class_name).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(info_frame, text="課題:", font=("", 9, "bold")).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=assignment_name, foreground="red", font=("", 9, "bold")).grid(
            row=1, column=1, sticky=tk.W, padx=(10, 0)
        )

        # 注意書き
        ttk.Label(
            main_frame,
            text="各学生フォルダ内の該当課題フォルダを削除します。\n"
                 "削除されたファイルはSharePointのごみ箱に移動し、\n"
                 "93日間は復元可能です。",
            font=("", 9),
            foreground="gray",
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 15))

        # 区切り線
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(0, 15))

        # 確認入力
        ttk.Label(
            main_frame,
            text="確認のため、課題名を入力してください:",
            font=("", 9),
        ).pack(anchor=tk.W, pady=(0, 5))

        self.confirm_var = tk.StringVar()
        self.confirm_var.trace("w", self._on_input_change)

        self.confirm_entry = ttk.Entry(
            main_frame,
            textvariable=self.confirm_var,
            width=50,
        )
        self.confirm_entry.pack(fill=tk.X, pady=(0, 5))
        self.confirm_entry.focus_set()

        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=15, side=tk.BOTTOM)

        self.delete_btn = ttk.Button(
            button_frame,
            text="削除する",
            command=self._on_delete,
            width=14,
            state=tk.DISABLED,
        )
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="キャンセル",
            command=self._on_cancel,
            width=14,
        ).pack(side=tk.LEFT, padx=5)

        # Enterキーで実行
        self.dialog.bind("<Return>", lambda e: self._on_delete())

    def _on_input_change(self, *args):
        """入力値が変わったら削除ボタンの有効/無効を切り替え"""
        if self.confirm_var.get().strip() == self.assignment_name:
            self.delete_btn.config(state=tk.NORMAL)
        else:
            self.delete_btn.config(state=tk.DISABLED)

    def _on_delete(self):
        if self.confirm_var.get().strip() == self.assignment_name:
            self.confirmed = True
            self.dialog.destroy()

    def _on_cancel(self):
        self.confirmed = False
        self.dialog.destroy()

    def show(self):
        """ダイアログを表示し、確認結果を返す"""
        self.dialog.wait_window()
        return self.confirmed


class DeleteCompleteDialog:
    """削除完了ダイアログ"""

    def __init__(self, parent, result):
        """
        Args:
            parent: 親ウィンドウ
            result: DeleteResult オブジェクト
        """
        self.dialog = create_centered_dialog(parent, "削除完了", 420, 300)

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        if result.cancelled:
            title_text = "削除がキャンセルされました"
            title_color = "orange"
        elif result.has_errors:
            title_text = "削除完了（一部エラーあり）"
            title_color = "orange"
        else:
            title_text = "削除完了"
            title_color = "green"

        ttk.Label(
            main_frame,
            text=title_text,
            font=("", 14, "bold"),
            foreground=title_color,
        ).pack(pady=(0, 20))

        # 統計
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(pady=(0, 15))

        ttk.Label(stats_frame, text=f"課題: {result.assignment_name}", font=("", 10)).pack(
            anchor=tk.W, pady=2
        )
        ttk.Label(stats_frame, text=f"対象学生数: {result.total_students}人", font=("", 10)).pack(
            anchor=tk.W, pady=2
        )
        ttk.Label(
            stats_frame,
            text=f"削除成功: {result.success_count}人",
            font=("", 10),
            foreground="green",
        ).pack(anchor=tk.W, pady=2)

        if result.skip_count > 0:
            ttk.Label(
                stats_frame,
                text=f"スキップ（課題なし）: {result.skip_count}人",
                font=("", 10),
                foreground="gray",
            ).pack(anchor=tk.W, pady=2)

        if result.fail_count > 0:
            ttk.Label(
                stats_frame,
                text=f"削除失敗: {result.fail_count}人",
                font=("", 10),
                foreground="red",
            ).pack(anchor=tk.W, pady=2)

            # エラー詳細
            ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
            error_results = [r for r in result.results if not r.success]
            for er in error_results[:5]:
                ttk.Label(
                    main_frame,
                    text=f"  {er.student_name}: {er.error}",
                    font=("", 8),
                    foreground="red",
                ).pack(anchor=tk.W)
            if len(error_results) > 5:
                ttk.Label(
                    main_frame,
                    text=f"  ...他 {len(error_results) - 5}件",
                    font=("", 8),
                    foreground="red",
                ).pack(anchor=tk.W)

        # 閉じるボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10, side=tk.BOTTOM)

        ttk.Button(
            button_frame,
            text="閉じる",
            command=self.dialog.destroy,
            width=12,
        ).pack()

    def show(self):
        self.dialog.wait_window()
