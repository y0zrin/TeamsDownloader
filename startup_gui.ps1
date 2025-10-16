# Teams課題ダウンローダー起動スクリプト

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Teams課題ダウンローダー 起動チェック" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Pythonのチェック
Write-Host "[1/5] Pythonのチェック..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK Python検出: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  NG Pythonが見つかりません" -ForegroundColor Red
    Write-Host "  https://www.python.org/ からインストールしてください" -ForegroundColor Red
    Read-Host "終了するにはEnterキーを押してください"
    exit 1
}

# 必須ライブラリのチェック
Write-Host ""
Write-Host "[2/5] 必須ライブラリのチェック..." -ForegroundColor Yellow

$requiredPackages = @(
    @{Name="msal"; Display="MSAL (Microsoft認証)"},
    @{Name="requests"; Display="Requests (HTTP通信)"}
)

$missingPackages = @()

foreach ($package in $requiredPackages) {
    $result = python -c "import $($package.Name)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $($package.Display)" -ForegroundColor Green
    } else {
        Write-Host "  NG $($package.Display) が見つかりません" -ForegroundColor Red
        $missingPackages += $package.Name
    }
}

# オプションライブラリのチェック
Write-Host ""
Write-Host "[3/5] オプションライブラリのチェック..." -ForegroundColor Yellow

$optionalPackages = @(
    @{Name="cryptography"; Display="Cryptography (暗号化)"; Note="キャッシュ暗号化に必要"},
    @{Name="openpyxl"; Display="OpenPyXL (Excel読み込み)"; Note="Excelファイル対応"},
    @{Name="pyperclip"; Display="PyperClip (クリップボード)"; Note="認証コード自動コピー"}
)

$missingOptionalPackages = @()

foreach ($package in $optionalPackages) {
    $result = python -c "import $($package.Name)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK $($package.Display)" -ForegroundColor Green
    } else {
        Write-Host "  - $($package.Display) が見つかりません ($($package.Note))" -ForegroundColor Yellow
        $missingOptionalPackages += $package.Name
    }
}

# 必須パッケージが不足している場合
if ($missingPackages.Count -gt 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "エラー: 必須ライブラリが不足しています" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "以下のコマンドを実行してインストールしてください:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  pip install $($missingPackages -join ' ') --break-system-packages" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "終了するにはEnterキーを押してください"
    exit 1
}

# オプションパッケージの推奨
if ($missingOptionalPackages.Count -gt 0) {
    Write-Host ""
    Write-Host "[推奨] 以下のライブラリをインストールすると機能が向上します:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  pip install $($missingOptionalPackages -join ' ') --break-system-packages" -ForegroundColor Cyan
    Write-Host ""
}

# ファイルチェック
Write-Host ""
Write-Host "[4/5] アプリケーションファイルのチェック..." -ForegroundColor Yellow

$requiredFiles = @(
    "main.py",
    "core/__init__.py",
    "services/__init__.py",
    "gui/__init__.py",
    "utils/__init__.py"
)

$allFilesExist = $true

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  OK $file" -ForegroundColor Green
    } else {
        Write-Host "  NG $file が見つかりません" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host ""
    Write-Host "エラー: 必要なファイルが不足しています" -ForegroundColor Red
    Read-Host "終了するにはEnterキーを押してください"
    exit 1
}

# 起動
Write-Host ""
Write-Host "[5/5] アプリケーションを起動します..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "起動中..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

python main.py

# 終了処理
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "エラーが発生しました (終了コード: $LASTEXITCODE)" -ForegroundColor Red
    Read-Host "終了するにはEnterキーを押してください"
}
