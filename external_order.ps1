# external_order.ps1
# This script is responsible for retrieving and processing external orders
# It also stores backups on Google Drive.

# Harman EDI processing for IN04, IN05, INSDES, DESADVD96A, DESADVD99A
# All files exchanged with Harman are stored in Google Drive and SFTP folders


$ErrorActionPreference = "Stop"

function Write-LogMessage {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Add-Content -Path $logfile
}

function Invoke-PythonScript {
    param([string]$script)
    
    if (-not $script) {
        Write-LogMessage "ERROR: Invoke-PythonScript requires exactly one argument."
        return 1
    }
    
    uv sync
    uv run python -m $script
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-LogMessage "Python processing $script completed."
    } else {
        Write-LogMessage "ERROR: Python processing $script failed with exit code: $exitCode"
    }
    
    return $exitCode
}

function Get-IncomingFiles {
    Write-LogMessage "Get incoming files from Harman SFTP: $sftp_insdes_dir"
    
    # Copy incoming files to sftp server archive, exit on error
    rclone copy "harmansftp:out_in04" "harmansftp/out_in04/archive" --exclude "archive/**" --no-traverse --log-file="$logfile"
    if ($LASTEXITCODE -ne 0) { exit 1 }
    
    rclone copy "harmansftp:out_insdes" "harmansftp/out_insdes/archive" --exclude "archive/**" --no-traverse --log-file="$logfile"
    if ($LASTEXITCODE -ne 0) { exit 1 }
    
    # Move incoming files to local directory
    rclone move "harmansftp:out_in04" "$workdir/harman/in" --exclude "archive/**" --no-traverse --log-file="$logfile"
    rclone move "harmansftp:out_insdes" "$workdir/harman/in" --exclude "archive/**" --no-traverse --log-file="$logfile"
}

function Publish-OutgoingFiles {
    Write-LogMessage "Publish outgoing files to Harman SFTP and Google Drive."
    
    # outgoing IN05 files to Google Drive
    rclone move $workdir/out "$gd_workdir/archive/out/in05" --include "*.XML" --fast-list  --checksum --log-file="$logfile"
    rclone copy "$gd_workdir/out/in05/send" "$gd_workdir/archive/out/in05" --include "*.XML" --fast-list --checksum --log-file="$logfile"

    # outgoing IN05 files to Harman SFTP, exit on error
    if ([datetime]::Now.Hour -ge 19) {
        Write-LogMessage "Publishing IN05 files to Harman SFTP."
        rclone copy "$gd_workdir/out/in05/send" "harmansftp:in_in05" --include "*.XML" --log-file="$logfile"
        if ($LASTEXITCODE -ne 0) { exit 1 }
        rclone move "$gd_workdir/out/in05/send" "harmansftp:in_in05/archive" --include "*.XML" --log-file="$logfile"
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    # outgoing DESADV files to Google Drive archive and Harman SFTP, exit on error
    rclone move "$workdir/desadvd" "$gd_workdir/out/desadvd96a" --include "*.DESADVD96A" --fast-list  --checksum --log-file="$logfile"
    rclone move "$workdir/desadvd" "$gd_workdir/out/desadvd99a" --include "*.DESADVD99A" --fast-list  --checksum --log-file="$logfile"
    rclone copy "$gd_workdir/out/desadvd96a" "$gd_workdir/archive/out/desadvd96a" --include "*.DESADVD96A" --fast-list  --checksum --log-file="$logfile"
    rclone copy "$gd_workdir/out/desadvd99a" "$gd_workdir/archive/out/desadvd99a" --include "*.DESADVD99A" --fast-list  --checksum --log-file="$logfile"
    
    # outgoing DESADV files to Harman SFTP, exit on error
    if ([datetime]::Now.Hour -ge 19) {
        Write-LogMessage "Publishing DESADV files to Harman SFTP."
        rclone copy "$gd_workdir/out/desadvd96a" "harmansftp:in_desadvd96a" --include "*.DESADVD96A" --log-file="$logfile"
        if ($LASTEXITCODE -ne 0) { exit 1 }
        rclone copy "$gd_workdir/out/desadvd99a" "harmansftp:in_desadvd99a" --include "*.DESADVD99A" --log-file="$logfile"
        if ($LASTEXITCODE -ne 0) { exit 1 }
        rclone move "$gd_workdir/out/desadvd96a" "harmansftp:in_desadvd96a/archive" --include "*.DESADVD96A" --log-file="$logfile"
        if ($LASTEXITCODE -ne 0) { exit 1 }
        rclone move "$gd_workdir/out/desadvd99a" "harmansftp:in_desadvd99a/archive" --include "*.DESADVD99A" --log-file="$logfile"
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
}

function Publish-OtherFiles {
    Write-LogMessage "Publish other files to Google Drive."
    # Copy digital files to Google Drive
    rclone copy "$workdir/digitals" "$gd_digitals" --fast-list --checksum --log-file="$logfile" --max-age 5d
    rclone move "$workdir/open_orders" "$gd_open_orders_dir" --delete-empty-src-dirs --log-file="$logfile"

    # Copy work files to Google Drive, processed, order and log files
    rclone copy "$workdir/harman/in" "$gd_workdir/archive/in/in04" --fast-list  --checksum --include "*.XML"  --log-file="$logfile"
    rclone sync "$workdir/harman/in" "$gd_workdir/archive/in/insdes" --fast-list  --checksum --log-file="$logfile"
    rclone copy "$workdir/logs" "$gd_workdir/logs" --fast-list --checksum --log-file="$logfile" --max-age 5d
}

function Invoke-Cleanup {
    $now = [datetime]::Now
    if ($now.Hour -eq 23 -and $now.Minute -lt 20) {
        rclone cleanup gautomation: --log-file="$logfile"
    }
}

$workdir = C:\Users\Administrator\projects-data\external_order
$logfile = Join-Path $work_dir "logs\external_order.log"
$gd_prepress = "gprepress:Drukproeven/Drukproeven_$(Get-Date -Format yyyy)"
$gd_digitals = "$gd_prepress/Harman-JBL"
$gd_open_orders = "$gd_prepress/000 - Visuals/open_orders"
$gd_workdir = "gautomation:Harman"


Write-Host "logfile: $logfile"
Write-Host "workdir: $workdir"
Write-Host "gd_digitals: $gd_digitals"
Write-Host "gd_open_orders: $gd_open_orders"
Write-Host "gd_workdir: $gd_workdir"

Write-LogMessage "`n--- Start of script ---`n"
Get-IncomingFiles
Invoke-PythonScript "src.main"
Publish-OutgoingFiles
Publish-OtherFiles
Invoke-Cleanup
Write-LogMessage "`n--- End of script ---`n"
