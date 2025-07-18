# PowerShell script to automate the database connection test and analysis.
# This script handles execution policy, virtual environment activation,
# dependency installation, and running the Python test script.

# --- Step 1: Set Execution Policy for the Current Process ---
# This allows the virtual environment activation script to run without
# changing your system's security settings permanently.
Write-Host "✅ Step 1: Setting PowerShell execution policy for this session..."
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -ErrorAction Stop
    Write-Host "✅ Execution policy set to 'RemoteSigned' successfully."
} catch {
    Write-Error "❌ Failed to set execution policy. Please run PowerShell as Administrator and try again."
    exit 1
}

# --- Step 2: Activate Virtual Environment ---
# Checks for the virtual environment and activates it.
Write-Host "`n✅ Step 2: Activating the Python virtual environment..."
$venvPath = ".\venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvPath)) {
    Write-Error "❌ Virtual environment not found at '$venvPath'."
    Write-Error "Please run 'python -m venv venv' to create it."
    exit 1
}

try {
    . $venvPath
    Write-Host "✅ Virtual environment activated successfully."
} catch {
    Write-Error "❌ Failed to activate the virtual environment."
    $_
    exit 1
}


# --- Step 3: Install/Update Python Dependencies ---
# Ensures all required packages from requirements.txt are installed.
Write-Host "`n✅ Step 3: Installing dependencies from requirements.txt..."
# We use python -m pip to ensure we're using the venv's pip
try {
    python -m pip install -r requirements.txt --log pip_install.log
    Write-Host "✅ Dependencies installed successfully. See pip_install.log for details."
} catch {
    Write-Error "❌ Failed to install dependencies. Check 'pip_install.log' for errors."
    exit 1
}


# --- Step 4: Run the Database Connection Test Script ---
# Executes the Python script to analyze the database.
Write-Host "`n✅ Step 4: Running the PostgreSQL database analysis script..."
$testScriptPath = ".\scripts\06_database\test_postgresql_connection.py"
if (-not (Test-Path $testScriptPath)) {
    Write-Error "❌ Database test script not found at '$testScriptPath'."
    exit 1
}

try {
    python $testScriptPath
} catch {
    Write-Error "❌ The database analysis script failed."
    $_
    exit 1
}

Write-Host "`n🎉 All steps completed."
Write-Host "Please review the output above for the database analysis results." 