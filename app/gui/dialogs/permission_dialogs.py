#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
権限確認ダイアログ
"""

import tkinter as tk
from tkinter import ttk
from gui.dialogs.dialog_utils import create_centered_dialog


class PermissionCheckDialog:
    """アクセス権限の確認結果を表示するダイアログ"""

    def __init__(self, parent, result):
        """
        Args:
            parent: 親ウィンドウ
            result: check_token_permissions() の戻り値 (dict)
        """
        self.dialog = create_centered_dialog(parent, "アクセス権限の確認", 460, 420)

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # タイトル
        ttk.Label(
            main_frame,
            text="アクセス権限の確認",
            font=("", 12, "bold"),
        ).pack(pady=(0, 15))

        # エラーがある場合
        if result.get("error"):
            ttk.Label(
                main_frame,
                text=result["error"],
                foreground="red",
                wraplength=400,
            ).pack(pady=10)
            self._add_close_button()
            return

        # ユーザー情報
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(info_frame, text="ユーザー:", font=("", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=result["user"]).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        expires_text = result["expires"]
        expires_color = "red" if result["is_expired"] else ""
        if result["is_expired"]:
            expires_text += " (期限切れ)"

        ttk.Label(info_frame, text="有効期限:", font=("", 9, "bold")).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=expires_text, foreground=expires_color).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # 区切り線
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # 書き込み権限の判定結果
        if result["has_write_permission"]:
            status_text = "書き込み権限あり"
            status_color = "green"
            status_detail = "付与済み: " + ", ".join(result["write_scopes_found"])
        else:
            status_text = "書き込み権限なし"
            status_color = "red"
            status_detail = "必要なスコープが見つかりません"

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(
            status_frame,
            text=status_text,
            font=("", 11, "bold"),
            foreground=status_color,
        ).pack(anchor=tk.W)

        ttk.Label(
            status_frame,
            text=status_detail,
            font=("", 9),
            foreground=status_color,
        ).pack(anchor=tk.W, padx=(5, 0))

        # 区切り線
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # スコープ一覧
        ttk.Label(
            main_frame,
            text="付与されたスコープ:",
            font=("", 9, "bold"),
        ).pack(anchor=tk.W)

        scope_frame = ttk.Frame(main_frame)
        scope_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))

        scope_text = tk.Text(
            scope_frame,
            height=6,
            width=50,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.NORMAL,
        )
        scrollbar = ttk.Scrollbar(scope_frame, orient=tk.VERTICAL, command=scope_text.yview)
        scope_text.configure(yscrollcommand=scrollbar.set)

        scope_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if result["scopes"]:
            scope_text.insert(tk.END, "\n".join(sorted(result["scopes"])))
        else:
            scope_text.insert(tk.END, "(スコープが見つかりませんでした)")
        scope_text.configure(state=tk.DISABLED)

        # 注記
        ttk.Label(
            main_frame,
            text="※ トークンレベルのスコープです。SharePointサイトレベルの権限は含みません。",
            font=("", 8),
            foreground="gray",
            wraplength=400,
        ).pack(anchor=tk.W, pady=(0, 5))

        # 閉じるボタン
        self._add_close_button()

    def _add_close_button(self):
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
