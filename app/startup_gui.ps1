# Teams課題ダウンローダー起動スクリプト

# ========================================
# Python バージョン設定（リリース時に見直す）
# ========================================
# 推奨系列: これより古い場合は最新版の自動インストールを案内する（パッチ版は python.org から自動取得）
$RecommendedPythonVersion = [Version]"3.14"
# 最低バージョン: これより古い場合は起動しない
$MinimumPythonVersion = [Version]"3.9"
$PythonDownloadUrl = "https://www.python.org/downloads/"
$PythonFtpUrl = "https://www.python.org/ftp/python/"

# 必須ライブラリ
$requiredPackages = @(
    @{Name="msal"; Display="MSAL (Microsoft認証)"},
    @{Name="requests"; Display="Requests (HTTP通信)"}
)

# オプションライブラリ
$optionalPackages = @(
    @{Name="cryptography"; Display="Cryptography (暗号化)"; Note="キャッシュ暗号化に必要"},
    @{Name="openpyxl"; Display="OpenPyXL (Excel読み込み)"; Note="Excelファイル対応"},
    @{Name="pyperclip"; Display="PyperClip (クリップボード)"; Note="認証コード自動コピー"},
    @{Name="olefile"; Display="olefile (DRM判定)"; Note="Excelファイルの保護状態チェック"}
)

# 使用する Python（Find-Python で決定）
$script:PythonExe = $null
$script:PythonVersion = $null

function Get-PythonVersionOf($exe) {
    try {
        $text = (& $exe --version 2>&1 | Out-String).Trim()
    } catch {
        return $null
    }
    # "Python 3.14.7" の形式でなければ無効（Microsoft Store のエイリアスは英語の案内文を出すだけ）
    $m = [regex]::Match($text, 'Python (\d+)\.(\d+)\.(\d+)')
    if (-not $m.Success) { return $null }
    return [Version]("{0}.{1}.{2}" -f $m.Groups[1].Value, $m.Groups[2].Value, $m.Groups[3].Value)
}

# インストール済みの Python をレジストリ (PEP 514) と PATH から探し、最も新しいものを返す
function Find-Python {
    $candidates = @()
    $roots = @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        foreach ($key in (Get-ChildItem $root -ErrorAction SilentlyContinue)) {
            $installKey = Join-Path $key.PSPath "InstallPath"
            if (-not (Test-Path $installKey)) { continue }
            $props = Get-ItemProperty $installKey -ErrorAction SilentlyContinue
            $exe = $props.ExecutablePath
            if (-not $exe -and $props.'(default)') { $exe = Join-Path $props.'(default)' "python.exe" }
            if ($exe -and (Test-Path $exe)) { $candidates += $exe }
        }
    }
    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath -and $onPath.Source) { $candidates += $onPath.Source }

    $best = $null
    foreach ($exe in ($candidates | Select-Object -Unique)) {
        $v = Get-PythonVersionOf $exe
        if ($v -and ((-not $best) -or ($v -gt $best.Version))) {
            $best = @{ Exe = $exe; Version = $v }
        }
    }
    return $best
}

function Test-PythonModule($moduleName) {
    & $script:PythonExe -c "import $moduleName" 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

# この PC のアーキテクチャに対応するインストーラーの種類
function Get-InstallerArch {
    $arch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
    switch ($arch) {
        "AMD64" { return @{ Suffix = "-amd64"; Label = "64-bit" } }
        "ARM64" { return @{ Suffix = "-arm64"; Label = "ARM64" } }
        default { return @{ Suffix = "";       Label = "32-bit" } }
    }
}

# 推奨系列の最新パッチ版と、この PC 向けインストーラーの URL を python.org から取得
function Get-LatestPythonInstaller {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $arch = Get-InstallerArch
    $series = "{0}.{1}" -f $RecommendedPythonVersion.Major, $RecommendedPythonVersion.Minor
    $index = Invoke-WebRequest -Uri $PythonFtpUrl -UseBasicParsing -TimeoutSec 30
    $pattern = 'href="(' + [regex]::Escape($series) + '\.\d+)/"'
    $versions = [regex]::Matches($index.Content, $pattern) | ForEach-Object { [Version]$_.Groups[1].Value } | Sort-Object -Unique -Descending
    foreach ($v in $versions) {
        # 正式版のインストーラーが存在する最新のものを採用（アルファ/RC のみのフォルダは読み飛ばす）
        $file = "python-$v$($arch.Suffix).exe"
        $url = "$PythonFtpUrl$v/$file"
        try {
            Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -TimeoutSec 30 | Out-Null
            return @{ Version = $v; Url = $url; File = $file; ArchLabel = $arch.Label }
        } catch { }
    }
    return $null
}

# 最新版 Python をダウンロードし、ユーザー単位でインストールする。成功したら $true
function Install-LatestPython {
    Write-Host "  最新版を確認中..." -ForegroundColor Yellow
    $latest = $null
    try { $latest = Get-LatestPythonInstaller } catch { }
    if (-not $latest) {
        Write-Host "  NG 最新版の情報を取得できませんでした。ブラウザでダウンロードページを開きます" -ForegroundColor Red
        Start-Process $PythonDownloadUrl
        return $false
    }
    Write-Host "  最新版: Python $($latest.Version) ($($latest.ArchLabel))" -ForegroundColor Green

    $installer = Join-Path $env:TEMP $latest.File
    Write-Host "  ダウンロード中... $($latest.File)" -ForegroundColor Yellow
    $oldProgress = $ProgressPreference
    $ProgressPreference = "SilentlyContinue"
    try {
        Invoke-WebRequest -Uri $latest.Url -OutFile $installer -UseBasicParsing -TimeoutSec 600
    } catch {
        Write-Host "  NG ダウンロードに失敗しました: $($_.Exception.Message)" -ForegroundColor Red
        Start-Process $PythonDownloadUrl
        return $false
    } finally {
        $ProgressPreference = $oldProgress
    }

    # 実行前に署名を確認（Python Software Foundation の署名でなければ中止）
    $sig = Get-AuthenticodeSignature $installer
    if ($sig.Status -ne "Valid" -or $sig.SignerCertificate.Subject -notmatch "Python Software Foundation") {
        Write-Host "  NG ダウンロードしたファイルの署名を確認できませんでした。中止します" -ForegroundColor Red
        Remove-Item $installer -ErrorAction SilentlyContinue
        return $false
    }
    Write-Host "  署名確認 OK (Python Software Foundation)" -ForegroundColor Green

    Write-Host "  インストール中... (インストーラーのウィンドウが閉じるまでお待ちください)" -ForegroundColor Yellow
    $proc = Start-Process -FilePath $installer -ArgumentList "/passive", "InstallAllUsers=0", "PrependPath=1", "Include_test=0" -Wait -PassThru
    Remove-Item $installer -ErrorAction SilentlyContinue
    if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
        Write-Host "  NG インストールに失敗しました (終了コード: $($proc.ExitCode))" -ForegroundColor Red
        return $false
    }

    # このセッションの PATH を更新し、新しい Python を探す
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $found = Find-Python
    if (-not $found -or $found.Version -lt $latest.Version) {
        Write-Host "  NG インストール後の Python を検出できませんでした。startup_gui.bat を実行し直してください" -ForegroundColor Red
        return $false
    }
    $script:PythonExe = $found.Exe
    $script:PythonVersion = $found.Version
    Write-Host "  OK Python $($found.Version) をインストールしました" -ForegroundColor Green
    return $true
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Teams課題ダウンローダー 起動チェック" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# Pythonのチェック
Write-Host "[1/5] Pythonのチェック..." -ForegroundColor Yellow

$justInstalledPython = $false
$found = Find-Python
if ($found) {
    $script:PythonExe = $found.Exe
    $script:PythonVersion = $found.Version
    Write-Host "  OK Python $PythonVersion ($PythonExe)" -ForegroundColor Green
}

if (-not $found -or $PythonVersion -lt $MinimumPythonVersion) {
    if (-not $found) {
        Write-Host "  NG Python が見つかりません" -ForegroundColor Red
    } else {
        Write-Host "  NG Python $MinimumPythonVersion 以降が必要です" -ForegroundColor Red
    }
    $answer = Read-Host "  最新版の Python をこの PC に合わせて自動インストールしますか？ [Y/n]"
    if ($answer -match '^[Nn]' -or -not (Install-LatestPython)) {
        Read-Host "終了するにはEnterキーを押してください"
        exit 1
    }
    $justInstalledPython = $true
}
elseif ($PythonVersion -lt $RecommendedPythonVersion) {
    Write-Host "  推奨: Python $RecommendedPythonVersion 以降 (最新版をこの PC に合わせて自動インストールできます)" -ForegroundColor Yellow
    $answer = Read-Host "  最新版をインストールしますか？ [y/N] (Enter でこのまま起動)"
    if ($answer -match '^[Yy]') {
        if (Install-LatestPython) {
            $justInstalledPython = $true
        } else {
            Write-Host "  現在の Python $PythonVersion で続行します" -ForegroundColor Yellow
        }
    }
}

# 必須ライブラリのチェック
Write-Host ""
Write-Host "[2/5] 必須ライブラリのチェック..." -ForegroundColor Yellow

$missingPackages = @()

foreach ($package in $requiredPackages) {
    if (Test-PythonModule $package.Name) {
        Write-Host "  OK $($package.Display)" -ForegroundColor Green
    } else {
        Write-Host "  NG $($package.Display) が見つかりません" -ForegroundColor Red
        $missingPackages += $package.Name
    }
}

# オプションライブラリのチェック
Write-Host ""
Write-Host "[3/5] オプションライブラリのチェック..." -ForegroundColor Yellow

$missingOptionalPackages = @()

foreach ($package in $optionalPackages) {
    if (Test-PythonModule $package.Name) {
        Write-Host "  OK $($package.Display)" -ForegroundColor Green
    } else {
        Write-Host "  - $($package.Display) が見つかりません ($($package.Note))" -ForegroundColor Yellow
        $missingOptionalPackages += $package.Name
    }
}

# 必須パッケージが不足している場合（Python を入れ替えた直後はライブラリが空になるためここに来る）
if ($missingPackages.Count -gt 0) {
    Write-Host ""
    if ($justInstalledPython) {
        # インストール直後は確認せずそのまま導入（オプションもまとめて入れる）
        $missingPackages += $missingOptionalPackages
        $missingOptionalPackages = @()
        Write-Host "  新しい Python にライブラリを導入します: $($missingPackages -join ' ')" -ForegroundColor Yellow
    } else {
        Write-Host "  必須ライブラリが不足しています: $($missingPackages -join ' ')" -ForegroundColor Red
        $answer = Read-Host "  今すぐインストールしますか？ [Y/n]"
        if ($answer -match '^[Nn]') {
            Write-Host "  手動で導入する場合: & `"$PythonExe`" -m pip install $($missingPackages -join ' ')" -ForegroundColor Cyan
            Read-Host "終了するにはEnterキーを押してください"
            exit 1
        }
    }

    Write-Host ""
    $pipLog = & $PythonExe -m pip install @missingPackages 2>&1 | ForEach-Object { Write-Host $_; "$_" }
    if ($LASTEXITCODE -ne 0 -and (($pipLog -join "`n") -match 'externally-managed-environment')) {
        # uv などで導入した Python は PEP 668 の保護があり通常の pip install を拒否するため、フラグ付きで再試行
        Write-Host ""
        Write-Host "  externally-managed 環境のため --break-system-packages を付けて再試行します" -ForegroundColor Yellow
        & $PythonExe -m pip install --break-system-packages @missingPackages
    }
    Write-Host ""

    $stillMissing = @()
    foreach ($name in $missingPackages) {
        if (-not (Test-PythonModule $name)) {
            $stillMissing += $name
        }
    }

    if ($stillMissing.Count -gt 0) {
        Write-Host "  NG インストールに失敗しました: $($stillMissing -join ', ')" -ForegroundColor Red
        Write-Host "  ネットワーク接続を確認して、startup_gui.bat を実行し直してください" -ForegroundColor Red
        Read-Host "終了するにはEnterキーを押してください"
        exit 1
    }

    Write-Host "  OK ライブラリをインストールしました" -ForegroundColor Green
}

# オプションパッケージの推奨
if ($missingOptionalPackages.Count -gt 0) {
    Write-Host ""
    Write-Host "[推奨] 以下を導入すると機能が向上します:" -ForegroundColor Yellow
    Write-Host "  & `"$PythonExe`" -m pip install $($missingOptionalPackages -join ' ')" -ForegroundColor Cyan
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

& $PythonExe main.py

# 終了処理
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "エラーが発生しました (終了コード: $LASTEXITCODE)" -ForegroundColor Red
    Read-Host "終了するにはEnterキーを押してください"
}
