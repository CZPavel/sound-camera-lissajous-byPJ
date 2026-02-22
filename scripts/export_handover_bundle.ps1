Param(
  [string]$OutputDir = ".\handover"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$zipPath = Join-Path $OutputDir "sound-loopback-lissajous_handover_$stamp.zip"

$include = @(
  "README.md",
  "project_context.md",
  "requirements.txt",
  "CHANGELOG.md",
  "LICENSE",
  "docs",
  "src",
  "tests",
  "context_sources",
  "scripts"
)

$tmpDir = Join-Path $env:TEMP "sll_handover_$stamp"
if (Test-Path $tmpDir) { Remove-Item -Recurse -Force $tmpDir }
New-Item -ItemType Directory -Path $tmpDir | Out-Null

foreach ($item in $include) {
  $sourcePath = Join-Path $repoRoot $item
  if (Test-Path $sourcePath) {
    Copy-Item -Path $sourcePath -Destination $tmpDir -Recurse -Force
  }
}

if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $tmpDir "*") -DestinationPath $zipPath
Remove-Item -Recurse -Force $tmpDir

Write-Host "Handover bundle created: $zipPath"
