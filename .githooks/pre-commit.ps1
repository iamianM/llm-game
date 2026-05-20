$ErrorActionPreference = "Stop"

$root = git rev-parse --show-toplevel
Set-Location $root

$staged = @(git diff --cached --name-only --diff-filter=ACMR)
if ($staged.Count -eq 0) {
  Write-Host "pre-commit: no staged files"
  exit 0
}

uv run python scripts/docs-health.py --staged

$pythonFiles = @($staged | Where-Object { $_ -like "*.py" })
if ($pythonFiles.Count -gt 0) {
  uv run ruff check -- $pythonFiles
}

$contentFiles = @($staged | Where-Object { $_ -like "content/*" -or $_ -like "data/balance/*" })
if ($contentFiles.Count -gt 0) {
  uv run python -m src.game.cli content lint
}

$webConfigFiles = @("web/package.json", "web/package-lock.json", "web/tsconfig.json")
$webFiles = @($staged | Where-Object {
  $_.StartsWith("web/") -and (
    @(".ts", ".tsx").Contains([IO.Path]::GetExtension($_)) -or
    $webConfigFiles.Contains($_)
  )
})
if ($webFiles.Count -gt 0) {
  Push-Location web
  npm run type-check
  Pop-Location
}
