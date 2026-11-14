#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
画面が固まったときの診断

メインスレッドが定期的に打つ「心拍」が途切れたら、
全スレッドのスタックをファイルに書き出す。
固まる原因（どのスレッドが何で止まっているか）を後から確認できる。
"""

import faulthandler
import os
import threading
import time
from datetime import datetime

# 心拍の間隔（ミリ秒）
HEARTBEAT_INTERVAL_MS = 1000

# 何秒途切れたら「固まっている」と判断するか
STALL_SECONDS = 5

# 連続して記録し続けないための間隔（秒）
REPORT_INTERVAL_SECONDS = 60

REPORT_FILE = "hang_report.txt"


class HangWatchdog:
    """画面の固まりを検知してスタックを記録する"""

    def __init__(self, root, report_path=REPORT_FILE, log=None):
        self.root = root
        self.report_path = os.path.abspath(report_path)
        self.log = log
        self.last_beat = time.time()
        self.grab_info = ""
        self.last_report = 0.0
        self.stopped = False

    def start(self):
        """監視を開始"""
        self._beat()

        thread = threading.Thread(target=self._watch, daemon=True, name="hang-watchdog")
        thread.start()

    def _beat(self):
        """メインスレッドの心拍（画面が動いている限り呼ばれ続ける）"""
        self.last_beat = time.time()

        # 入力を掴んでいるウィンドウ（モーダルダイアログ）を控えておく
        try:
            grab = self.root.grab_current()
            self.grab_info = str(grab) if grab else ""
        except Exception:
            self.grab_info = ""

        try:
            self.root.after(HEARTBEAT_INTERVAL_MS, self._beat)
        except Exception:
            # ウィンドウが閉じられた
            self.stopped = True

    def _watch(self):
        """別スレッドから心拍を監視"""
        while not self.stopped:
            time.sleep(1)

            delay = time.time() - self.last_beat

            if delay < STALL_SECONDS:
                continue

            if time.time() - self.last_report < REPORT_INTERVAL_SECONDS:
                continue

            self._write_report(delay)
            self.last_report = time.time()

    def _write_report(self, delay):
        """全スレッドのスタックを記録"""
        try:
            with open(self.report_path, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 70 + "\n")
                f.write(
                    f"{datetime.now():%Y-%m-%d %H:%M:%S} "
                    f"画面が {delay:.1f} 秒応答していません\n"
                )

                if self.grab_info:
                    f.write(f"入力を掴んでいるウィンドウ: {self.grab_info}\n")

                f.write(f"スレッド数: {threading.active_count()}\n")
                f.write("-" * 70 + "\n")
                f.flush()

                # 全スレッドのスタックを出力
                faulthandler.dump_traceback(file=f, all_threads=True)

            if self.log:
                self.log(f"⚠️ 画面の停止を検知しました。詳細: {self.report_path}")

        except Exception:
            pass
