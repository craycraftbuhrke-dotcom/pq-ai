param(
  [string]$NodePath = "node"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$versionText = & $NodePath --version
if ($LASTEXITCODE -ne 0) { throw "Node.js was not found. Prepare Node.js 25.5 or newer on the offline build machine." }
$version = [version]($versionText.TrimStart("v").Split("-")[0])
if ($version -lt [version]"25.5.0") { throw "Single executable build requires Node.js 25.5 or newer. Current version: $versionText." }

New-Item -ItemType Directory -Path "$root\dist" -Force | Out-Null
& $NodePath --build-sea "$root\sea-config.json"
if ($LASTEXITCODE -ne 0) { throw "Single executable build failed." }

Copy-Item "$root\agent-config.template.ini" "$root\dist\agent-config.template.ini" -Force
Write-Host "Build completed: $root\dist\pq-upper-agent.exe"
Write-Host "The target computer needs the executable, configuration, certificates, and, when DURR_APPROVED_ADAPTER is used, the factory-approved adapter program. No Node.js installation or online dependency download is required."
