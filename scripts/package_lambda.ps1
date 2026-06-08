# package_lambda.ps1
# Builds deployment.zip for AWS Lambda upload
# Run from project root: .\scripts\package_lambda.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PackageDir  = Join-Path $ProjectRoot "package"
$OutputZip   = Join-Path $ProjectRoot "deployment.zip"
$Venv        = Join-Path $ProjectRoot ".venv"
$Pip         = Join-Path $Venv "Scripts\pip.exe"

Write-Host "=== Lambda Packaging Script ===" -ForegroundColor Cyan

# Step 1 — clean previous build
if (Test-Path $PackageDir) {
    Write-Host "Cleaning previous package dir..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $PackageDir
}
if (Test-Path $OutputZip) {
    Write-Host "Removing previous deployment.zip..." -ForegroundColor Yellow
    Remove-Item -Force $OutputZip
}

# Step 2 — install dependencies into package/
Write-Host "Installing dependencies into package/..." -ForegroundColor Cyan
& $Pip install fastapi mangum pydantic pydantic-core uvicorn python-dotenv `
        anyio sniffio starlette typing_extensions annotated-types `
        -t $PackageDir --quiet

# Step 3 — copy application code
Write-Host "Copying application code..." -ForegroundColor Cyan
Copy-Item -Recurse -Force (Join-Path $ProjectRoot "app")  (Join-Path $PackageDir "app")
Copy-Item -Recurse -Force (Join-Path $ProjectRoot "eval") (Join-Path $PackageDir "eval")

# Step 4 — copy lambda handler to package root
Write-Host "Copying lambda_handler.py to package root..." -ForegroundColor Cyan
Copy-Item -Force (Join-Path $ProjectRoot "app\lambda_handler.py") (Join-Path $PackageDir "lambda_handler.py")

# Step 5 — create ZIP from package contents
Write-Host "Creating deployment.zip..." -ForegroundColor Cyan
Push-Location $PackageDir
Compress-Archive -Path ".\*" -DestinationPath $OutputZip -Force
Pop-Location

# Step 6 — report size
$ZipSize = (Get-Item $OutputZip).Length / 1MB
Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host ("deployment.zip size: {0:N1} MB" -f $ZipSize) -ForegroundColor Green

if ($ZipSize -gt 50) {
    Write-Host "WARNING: ZIP exceeds 50MB Lambda limit. Lambda Layer required." -ForegroundColor Red
} else {
    Write-Host "Size is within Lambda 50MB limit. Ready to upload." -ForegroundColor Green
}

# Step 7 — clean up package dir
Write-Host "Cleaning up package dir..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $PackageDir

Write-Host ""
Write-Host "Output: $OutputZip" -ForegroundColor Cyan
