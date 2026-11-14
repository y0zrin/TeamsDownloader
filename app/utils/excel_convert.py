#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excelファイル → CSV 変換ユーティリティ

SharePointの名簿はIRM(暗号化)保護されていることがあり、
その場合はopenpyxlで読み込めないため、Windows上のExcelを使って変換する。
（手作業の「Excelで開く → CSV UTF-8 で保存」を自動化したもの）
"""

import csv
import os
import subprocess
from datetime import date, datetime

# ExcelのSaveAsフォーマット
_XL_CSV_UTF8 = 62   # Excel 2016以降
_XL_CSV = 6         # 従来のCSV（日本語環境ではShift_JIS）

# Excel変換のタイムアウト（秒）
EXCEL_TIMEOUT = 180

OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def is_protected_office_file(path):
    """openpyxlで読めない形式（IRM保護/旧xls）かどうかを判定

    IRM(暗号化)保護されたxlsxや旧.xlsは、実体がOLE複合ドキュメントになる。
    """
    try:
        with open(path, 'rb') as f:
            return f.read(8) == OLE_SIGNATURE
    except OSError:
        return False


def _format_cell(value):
    """Excelのセル値をCSV用の文字列に変換"""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y/%m/%d")
    return str(value)


def _convert_with_openpyxl(xlsx_path, tmp_path, log):
    """openpyxlでxlsxをCSVに変換"""
    try:
        from openpyxl import load_workbook
    except ImportError:
        log("⚠️ openpyxlがインストールされていません")
        return False

    wb = None
    try:
        wb = load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active

        row_count = 0
        with open(tmp_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                # 完全に空の行はスキップ
                if all(v is None for v in row):
                    continue
                writer.writerow([_format_cell(v) for v in row])
                row_count += 1

        return row_count >= 2

    except Exception as e:
        log(f"   openpyxlでは読み込めませんでした: {e}")
        return False

    finally:
        if wb is not None:
            try:
                wb.close()
            except Exception:
                pass


def _ps_quote(value):
    """PowerShellのシングルクォート文字列としてエスケープ"""
    return "'" + str(value).replace("'", "''") + "'"


def _build_excel_script(xlsx_path, csv_path):
    """Excel(COM)でCSVに保存するPowerShellスクリプトを生成

    IRM保護されたブックは直接SaveAsできない（権限エラーになる）ため、
    シートを新規ブックにコピーしてからCSVとして保存する。
    """
    return f"""
$ErrorActionPreference = 'Stop'
$src = {_ps_quote(xlsx_path)}
$dst = {_ps_quote(csv_path)}
$code = 1
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
$wb = $null
$copy = $null
try {{
    $wb = $excel.Workbooks.Open($src, 0, $true)
    # IRM保護されたブックはそのままCSV保存できないため、シートを新規ブックへコピー
    $wb.ActiveSheet.Copy()
    $copy = $excel.ActiveWorkbook
    try {{
        $copy.SaveAs($dst, {_XL_CSV_UTF8})
    }} catch {{
        $copy.SaveAs($dst, {_XL_CSV})
    }}
    $code = 0
}} catch {{
    Write-Output ("ERROR: " + $_.Exception.Message)
}} finally {{
    if ($copy -ne $null) {{ try {{ $copy.Close($false) }} catch {{}} }}
    if ($wb -ne $null) {{ try {{ $wb.Close($false) }} catch {{}} }}
    try {{ $excel.Quit() }} catch {{}}
}}
exit $code
"""


def _convert_with_excel(xlsx_path, tmp_path, log):
    """Windows上のExcel(COM)を使ってCSVに変換

    IRM保護された名簿も、ログイン中のユーザーの権限でExcelが復号できるため、
    Excelに「CSV UTF-8で保存」させる。
    """
    if os.name != 'nt':
        log("⚠️ Excel経由の変換はWindowsでのみ利用できます")
        return False

    log("📊 Excelを使ってCSVに変換しています...")

    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive",
                "-ExecutionPolicy", "Bypass", "-Command",
                _build_excel_script(xlsx_path, tmp_path),
            ],
            capture_output=True,
            timeout=EXCEL_TIMEOUT,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except FileNotFoundError:
        log("⚠️ PowerShellが見つかりません")
        return False
    except subprocess.TimeoutExpired:
        log("⚠️ Excelでの変換がタイムアウトしました")
        return False

    if result.returncode != 0 or not os.path.exists(tmp_path):
        output = (result.stdout or b'') + (result.stderr or b'')
        message = output.decode('cp932', errors='replace').strip()
        if message:
            # PowerShellのエラーは長いので先頭行のみ
            log(f"⚠️ Excelでの変換に失敗しました: {message.splitlines()[0]}")
        else:
            log("⚠️ Excelでの変換に失敗しました（Excelがインストールされていない可能性があります）")
        return False

    return _ensure_utf8(tmp_path, log)


def _ensure_utf8(csv_path, log):
    """CSVをUTF-8(BOM付き)に揃える

    ExcelがxlCSVUTF8に対応していない場合はShift_JISで保存されるため、
    読み込み側（utf-8-sig）に合わせて変換する。
    """
    try:
        raw = open(csv_path, 'rb').read()
    except OSError as e:
        log(f"⚠️ 変換後のCSVを読み込めません: {e}")
        return False

    if not raw.strip():
        log("⚠️ 変換後のCSVが空です")
        return False

    for encoding in ('utf-8-sig', 'cp932'):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue

        if encoding != 'utf-8-sig':
            with open(csv_path, 'wb') as f:
                f.write(text.encode('utf-8-sig'))
            log("   Shift_JIS → UTF-8 に変換しました")
        return True

    log("⚠️ 変換後のCSVの文字コードを判別できませんでした")
    return False


def convert_xlsx_to_csv(xlsx_path, csv_path, log=print):
    """名簿(.xlsx)をCSV(UTF-8 BOM)に変換

    1. openpyxlで変換（通常のxlsx）
    2. 失敗したらExcel経由で変換（IRM保護された名簿・旧xls）

    変換に成功するまで既存のCSVは書き換えない。

    Returns:
        変換に成功したらTrue
    """
    xlsx_path = os.path.abspath(xlsx_path)
    csv_path = os.path.abspath(csv_path)
    tmp_path = csv_path + ".tmp.csv"

    if not os.path.exists(xlsx_path):
        log(f"⚠️ 変換元のファイルがありません: {xlsx_path}")
        return False

    def cleanup():
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    cleanup()

    try:
        protected = is_protected_office_file(xlsx_path)
        if protected:
            log("🔒 名簿はIRM(暗号化)保護されています")

        converted = False
        if not protected:
            converted = _convert_with_openpyxl(xlsx_path, tmp_path, log)

        if not converted:
            cleanup()
            converted = _convert_with_excel(xlsx_path, tmp_path, log)

        if not converted:
            return False

        os.replace(tmp_path, csv_path)
        log(f"📄 CSVに変換しました: {os.path.basename(csv_path)}")
        return True

    finally:
        cleanup()
