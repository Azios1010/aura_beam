

param(
    [string]$PythonExe = "python",
    [int]$StartRun = 1,
    [int]$EndRun = 5
)
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

for ($i = $StartRun; $i -le $EndRun; $i++) {
    $runName = "run_{0:d2}" -f $i
    Write-Host "=== Running B1-B2 :: $runName ==="
    & $PythonExe run_experiment_suite.py --config configs/q2_b1_b2_suite.json --run-name $runName
}

Write-Host "=== Aggregating B1-B2 results ==="
& $PythonExe aggregate_results.py --results-root artifacts/results_q2_b1_b2 --output-csv artifacts/tables/q2_b1_b2_results.csv

Write-Host "Done. Output CSV: artifacts/tables/q2_b1_b2_results.csv"
