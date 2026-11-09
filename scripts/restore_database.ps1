param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [Parameter(Mandatory = $false)]
    [string]$StagingDatabaseUrl = $env:STAGING_DATABASE_URL
)

if (-not (Test-Path $BackupFile)) {
    throw "File backup tidak ditemukan: $BackupFile"
}
if (-not $StagingDatabaseUrl) {
    throw "STAGING_DATABASE_URL wajib diset dan harus menunjuk ke database staging."
}
if ($StagingDatabaseUrl.StartsWith("postgresql+psycopg://")) {
    $StagingDatabaseUrl = $StagingDatabaseUrl.Replace("postgresql+psycopg://", "postgresql://")
}

Write-Warning "Restore dijalankan hanya ke database staging. Jangan gunakan database produksi sebagai tujuan uji."
& pg_restore --clean --if-exists --no-owner --dbname="$StagingDatabaseUrl" "$BackupFile"
if ($LASTEXITCODE -ne 0) {
    throw "Restore staging gagal."
}
Write-Output "Restore staging berhasil."
