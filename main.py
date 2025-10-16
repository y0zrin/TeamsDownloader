#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teams課題ダウンローダー - メインエントリーポイント
"""

import tkinter as tk
from gui.main_window import TeamsDownloaderGUI


def main():
    root = tk.Tk()
    app = TeamsDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
