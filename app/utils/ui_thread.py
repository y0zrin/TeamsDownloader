#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI操作をメインスレッドで実行するためのヘルパー

Tkinterはメインスレッド以外から操作するとフリーズやデッドロックを起こす。
特にモーダルダイアログ（grab_set）をワーカースレッドから作ると、
ウィンドウ全体が操作できなくなることがある。
"""

import threading


def run_on_main_thread(root, func, *args, **kwargs):
    """UI操作をメインスレッドで実行し、結果を返す

    メインスレッドから呼ばれた場合はそのまま実行する。
    ワーカースレッドから呼ばれた場合はメインスレッドに処理を依頼し、
    完了するまで待つ（ダイアログの場合はユーザーが閉じるまで）。

    Args:
        root: ルートウィンドウ
        func: 実行する関数
        *args, **kwargs: funcに渡す引数

    Returns:
        funcの戻り値
    """
    if threading.current_thread() is threading.main_thread():
        return func(*args, **kwargs)

    done = threading.Event()
    box = {}

    def runner():
        try:
            box['result'] = func(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001 - 呼び出し元で再送出する
            box['error'] = e
        finally:
            done.set()

    root.after(0, runner)
    done.wait()

    if 'error' in box:
        raise box['error']

    return box.get('result')
