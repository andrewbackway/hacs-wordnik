#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Bump the Wordnik integration version, commit, tag and push a release.

.DESCRIPTION
    Reads the current version from custom_components/wordnik/manifest.json,
    increments it (patch by default), writes the new version to both
    manifest.json and const.py, then commits, creates a "vX.Y.Z" tag and
    pushes both the branch and the tag so HACS can pick up the release.

.PARAMETER Bump
    Which part to increment: patch (default), minor or major.

.PARAMETER Version
    Set an explicit version (e.g. 1.2.3) instead of incrementing.

.PARAMETER Remote
    Git remote to push to. Defaults to "origin".

.PARAMETER NoPush
    Make the commit and tag locally but do not push.

.EXAMPLE
    ./scripts/release.ps1                # 0.1.1 -> 0.1.2
    ./scripts/release.ps1 -Bump minor    # 0.1.1 -> 0.2.0
    ./scripts/release.ps1 -Version 1.0.0 # set explicitly
#>
[CmdletBinding()]
param(
    [ValidateSet("patch", "minor", "major")]
    [string]$Bump = "patch",
    [string]$Version,
    [string]$Remote = "origin",
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"

# Resolve paths relative to the repo root (parent of this script's folder).
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $RepoRoot "custom_components/wordnik/manifest.json"
$ConstPath = Join-Path $RepoRoot "custom_components/wordnik/const.py"

foreach ($path in @($ManifestPath, $ConstPath)) {
    if (-not (Test-Path $path)) {
        throw "Required file not found: $path"
    }
}

# Read current version from the manifest.
$manifestRaw = Get-Content $ManifestPath -Raw
if ($manifestRaw -notmatch '"version"\s*:\s*"(?<v>\d+\.\d+\.\d+)"') {
    throw "Could not find a semantic version in $ManifestPath"
}
$current = $Matches.v
Write-Host "Current version: $current"

# Determine the new version.
if ($Version) {
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "Explicit -Version must be in X.Y.Z form, got '$Version'"
    }
    $new = $Version
}
else {
    $parts = $current.Split(".")
    [int]$major = $parts[0]
    [int]$minor = $parts[1]
    [int]$patch = $parts[2]
    switch ($Bump) {
        "major" { $major++; $minor = 0; $patch = 0 }
        "minor" { $minor++; $patch = 0 }
        "patch" { $patch++ }
    }
    $new = "$major.$minor.$patch"
}
Write-Host "New version:     $new"

if ($new -eq $current) {
    throw "New version matches current version ($current); nothing to do."
}

# Refuse to run on a dirty tree so the release commit only contains the bump.
$dirty = git -C $RepoRoot status --porcelain
if ($dirty) {
    throw "Working tree is not clean. Commit or stash changes first:`n$dirty"
}

# Update manifest.json (preserves surrounding formatting).
$manifestRaw = $manifestRaw -replace '("version"\s*:\s*")\d+\.\d+\.\d+(")', "`${1}$new`${2}"
Set-Content -Path $ManifestPath -Value $manifestRaw -NoNewline

# Update const.py VERSION constant.
$constRaw = Get-Content $ConstPath -Raw
if ($constRaw -notmatch 'VERSION\s*:\s*Final\s*=\s*"\d+\.\d+\.\d+"') {
    throw "Could not find VERSION constant in $ConstPath"
}
$constRaw = $constRaw -replace '(VERSION\s*:\s*Final\s*=\s*")\d+\.\d+\.\d+(")', "`${1}$new`${2}"
Set-Content -Path $ConstPath -Value $constRaw -NoNewline

$tag = "v$new"
Write-Host "Committing and tagging $tag ..."

git -C $RepoRoot add "custom_components/wordnik/manifest.json" "custom_components/wordnik/const.py"
git -C $RepoRoot commit -m "Release $tag"
git -C $RepoRoot tag $tag

if ($NoPush) {
    Write-Host "NoPush set: created commit and tag $tag locally. Push manually when ready:"
    Write-Host "  git push $Remote HEAD"
    Write-Host "  git push $Remote $tag"
    return
}

$branch = git -C $RepoRoot rev-parse --abbrev-ref HEAD
Write-Host "Pushing branch '$branch' and tag '$tag' to '$Remote' ..."
git -C $RepoRoot push $Remote $branch
git -C $RepoRoot push $Remote $tag

Write-Host ""
Write-Host "Done. Now publish a GitHub release for tag $tag so HACS offers the update:"
Write-Host "  https://github.com/andrewbackway/hacs-wordnik/releases/new?tag=$tag"
