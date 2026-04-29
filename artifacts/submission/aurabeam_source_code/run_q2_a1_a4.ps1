

param(
    [string]$PythonExe = "python",
    [int]$StartRun = 1,
    [int]$EndRun = 5
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

for ($i = $StartRun; $i -le $EndRun; $i++) {
    $runName = "run_{0:d2}" -f $i
    Write-Host "=== Running A1-A4 :: $runName ==="
    & $PythonExe run_experiment_suite.py --config configs/q2_a1_a4_suite.json --run-name $runName
}

Write-Host "=== Aggregating A1-A4 results ==="
& $PythonExe aggregate_results.py --results-root artifacts/results_q2_a1_a4 --output-csv artifacts/tables/q2_a1_a4_results.csv

Write-Host "Done. Output CSV: artifacts/tables/q2_a1_a4_results.csv"
