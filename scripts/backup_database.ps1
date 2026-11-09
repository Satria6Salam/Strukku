param(
    [Parameter(Mandatory = $false)]
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [string]$BackupDirectory = ".\storage\backups"
)

if (-not $DatabaseUrl) {
    throw "DATABASE_URL wajib diset melalui environment atau parameter."
}
if ($DatabaseUrl -match '^sqlite') {
    throw "Backup PostgreSQL/Supabase memerlukan DATABASE_URL PostgreSQL. Untuk SQLite gunakan copy database secara aman setelah proses berhenti."
}
if ($DatabaseUrl.StartsWith("postgresql+psycopg://")) {
    $DatabaseUrl = $DatabaseUrl.Replace("postgresql+psycopg://", "postgresql://")
}

New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $BackupDirectory "strukku-$timestamp.dump"
& pg_dump "$DatabaseUrl" --format=custom --no-owner --file="$backupFile"
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump gagal."
}
Write-Output $backupFile
