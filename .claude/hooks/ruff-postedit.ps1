#Requires -Version 7
# PostToolUse hook: run `ruff check --fix` + `ruff format` on edited Python files
# inside BACKEND/ or MONGO_DB/. Reads Claude Code hook payload from stdin.
$ErrorActionPreference = 'Continue'

try {
    $payload = [Console]::In.ReadToEnd() | ConvertFrom-Json
} catch {
    exit 0
}

$filePath = $payload.tool_input.file_path
if (-not $filePath -and $payload.tool_response) {
    $filePath = $payload.tool_response.filePath
}
if (-not $filePath) { exit 0 }
if ($filePath -notmatch '\.py$') { exit 0 }

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$project = $null
if ($filePath -match '[/\\]BACKEND[/\\]')  { $project = Join-Path $repoRoot 'BACKEND' }
elseif ($filePath -match '[/\\]MONGO_DB[/\\]') { $project = Join-Path $repoRoot 'MONGO_DB' }
if (-not $project) { exit 0 }
if (-not (Test-Path -LiteralPath $filePath)) { exit 0 }

& uv run --project $project ruff check --fix $filePath
& uv run --project $project ruff format $filePath

exit 0
