# Install one or all skills from this repo into ~/.claude/skills/.
#
# Usage:
#   .\install\install.ps1                    # install every available skill
#   .\install\install.ps1 codemap            # install a single skill
#   .\install\install.ps1 -Symlink           # symlink instead of copy (auto-updates on git pull)
#   .\install\install.ps1 codemap -Symlink

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Skills,
    [switch]$Symlink
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$TargetBase = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $env:USERPROFILE ".claude\skills" }

# Discover available skills (folders containing a SKILL.md).
$Available = @()
Get-ChildItem -Path $RepoRoot -Directory | ForEach-Object {
    if (Test-Path (Join-Path $_.FullName "SKILL.md")) {
        $Available += $_.Name
    }
}

if (-not $Skills -or $Skills.Count -eq 0) {
    $Skills = $Available
}

if ($Skills.Count -eq 0) {
    Write-Error "No installable skills found in $RepoRoot"
    exit 1
}

if (-not (Test-Path $TargetBase)) {
    New-Item -ItemType Directory -Path $TargetBase -Force | Out-Null
}

foreach ($skill in $Skills) {
    $src = Join-Path $RepoRoot $skill
    if (-not (Test-Path (Join-Path $src "SKILL.md"))) {
        Write-Warning "skip: $skill (no SKILL.md)"
        continue
    }
    $dst = Join-Path $TargetBase $skill
    if (Test-Path $dst) {
        Remove-Item -Recurse -Force $dst
    }
    if ($Symlink) {
        New-Item -ItemType SymbolicLink -Path $dst -Target $src | Out-Null
        Write-Host "symlinked $skill -> $dst"
    } else {
        Copy-Item -Recurse -Path $src -Destination $dst
        Write-Host "installed $skill -> $dst"
    }
}
