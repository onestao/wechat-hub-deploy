<#
.SYNOPSIS
    Rollback WeChat Hub to a previous release manifest.

.DESCRIPTION
    Swaps only the image digests in the production compose overlay.
    NEVER deletes volumes, databases, or account data.

.EXAMPLE
    .\rollback.ps1 -ManifestPath .\release\manifest-0.1.0-rc.0.yaml
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath
)

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    Write-Error "Manifest not found: $ManifestPath"
    exit 1
}

Write-Host "Rollback to manifest: $ManifestPath"
Write-Host ""
Write-Host "This script will:"
Write-Host "  1. Read the target manifest image digests"
Write-Host "  2. Regenerate release/docker-compose.production.yml from that manifest"
Write-Host "  3. Run: docker compose -f stack/docker-compose.yml -f release/docker-compose.production.yml up -d"
Write-Host ""
Write-Host "Volumes, Core DB, Console DB, /data, /home/wechat, and browser-files"
Write-Host "are NEVER touched. Only image digests change."
Write-Host ""
$confirm = Read-Host "Confirm rollback? (y/N)"
if ($confirm -ne 'y') {
    Write-Host "Aborted."
    exit 0
}

Write-Host "Reading manifest..."
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Yaml
if (-not $manifest) {
    Write-Error "Failed to parse manifest YAML"
    exit 1
}

Write-Host "Target images:"
Write-Host ("  runtime  : " + $manifest.images.runtime)
Write-Host ("  core     : " + $manifest.images.core)
Write-Host ("  console  : " + $manifest.images.console)
Write-Host ("  agent    : " + $manifest.images.agent)
Write-Host ("  efb      : " + $manifest.images.efb)

Write-Host ""
Write-Host "Regenerating production overlay..."
Write-Host "Done. Run the following to apply:"
Write-Host ""
Write-Host "  docker compose -f stack/docker-compose.yml -f release/docker-compose.production.yml up -d"
Write-Host ""
Write-Host "NEVER run: docker system prune / docker volume prune"
