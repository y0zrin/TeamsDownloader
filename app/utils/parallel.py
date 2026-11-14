#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API呼び出しの並列実行ヘルパー

SharePointは1リクエストあたりの往復時間が長いため、
学生ごとの問い合わせを並列化すると待ち時間を大幅に短縮できる。
"""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

# 既定の並列数（Graph APIのスロットリングを避けつつ効果が出る値）
DEFAULT_WORKERS = 6

# キャンセル確認の間隔（秒）
POLL_INTERVAL = 0.2


def _detach_threads(executor):
    """打ち切ったワーカースレッドを、終了時の待ち合わせ対象から外す

    concurrent.futures はインタプリタ終了時に全ワーカーの終了を待つため、
    応答の無い通信を抱えたスレッドが残っているとアプリが閉じられなくなる。
    キャンセル時のみ使用する（通常終了時は全タスクが完了している）。
    """
    try:
        from concurrent.futures import thread as thread_module

        for worker in getattr(executor, "_threads", ()):
            thread_module._threads_queues.pop(worker, None)
    except Exception:
        pass


def imap_unordered(items, task, max_workers=DEFAULT_WORKERS, should_cancel=None,
                   poll_interval=POLL_INTERVAL):
    """itemsを並列実行し、完了順に (item, result, error) を返すジェネレータ

    should_cancel が指定された場合、結果を待っている間も poll_interval ごとに
    確認する。APIが応答しない・スロットリングで待たされている状況でも
    キャンセルが効くようにするため、結果の到着を待ち続けない。

    呼び出し側がbreakした場合やキャンセルされた場合は、
    未実行のタスクをキャンセルしてから終了する。

    Args:
        items: 処理対象のリスト
        task: item を受け取って結果を返す関数
        max_workers: 並列数
        should_cancel: キャンセル判定の関数（Trueを返すと打ち切る）
        poll_interval: キャンセル確認の間隔（秒）

    Yields:
        (item, result, error): 失敗した場合は result=None, error=例外
    """
    items = list(items)
    if not items:
        return

    executor = ThreadPoolExecutor(max_workers=max_workers)
    completed = False

    try:
        futures = {executor.submit(task, item): item for item in items}
        pending = set(futures)

        while pending:
            if should_cancel and should_cancel():
                # 実行中のタスクの完了を待たずに打ち切る
                return

            done, pending = wait(
                pending,
                timeout=poll_interval if should_cancel else None,
                return_when=FIRST_COMPLETED,
            )

            for future in done:
                item = futures[future]
                try:
                    yield item, future.result(), None
                except Exception as e:  # noqa: BLE001 - 呼び出し側でログする
                    yield item, None, e

        completed = True

    finally:
        executor.shutdown(wait=False, cancel_futures=True)
        if not completed:
            # 応答待ちのスレッドがアプリの終了を妨げないようにする
            _detach_threads(executor)
