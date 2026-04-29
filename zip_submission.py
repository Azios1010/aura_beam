import os
import shutil
import zipfile
from pathlib import Path

# Base directory
base_dir = Path(r"c:\Users\ADMIN\OneDrive\Máy tính\CV Model")

# Output directories
submission_dir = base_dir / "artifacts" / "submission"
staging_dir = submission_dir / "aurabeam_source_code"
zip_path = submission_dir / "aurabeam_source_code.zip"

# Clean up staging dir if it exists
if staging_dir.exists():
    shutil.rmtree(staging_dir)
staging_dir.mkdir(parents=True, exist_ok=True)

# Define what to include based on README_SUBMISSION.md
include_dirs = [
    "src", "scripts", "configs", "firmware", "tests", "notebooks",
    "fogging_1", "rain_1", "thunder_1", "night_1", "norm_1",
    "artifacts/tables", "artifacts/figures/q2_ready_figures",
    "artifacts/results_q2_a1_a4", "artifacts/results_q2_b1_b2",
    "artifacts/results_q2_c1_c4", "artifacts/results_final_q2_lock",
    "metrics_ultralytics/ensemble"
]

include_files = [
    "model/yolov5.pt", "model/model_ai.pt",
    "demo_video/fogging_1.mp4", "demo_video/rain_1.mp4",
    "demo_video/thunder_1.mp4", "demo_video/night_1.mp4",
    "demo_video/norm_1.mp4",
    "metrics_ultralytics/each_model/five_case.csv",
    "requirements.txt", "SETUP.md", "PROJECT_STRUCTURE.md",
    "AGENTS.md", ".gitignore", "run_experiment_suite.py",
    "evaluate_metrics.py", "aggregate_results.py",
    "run_q2_a1_a4.ps1", "run_q2_b1_b2.ps1", "run_q2_c1_c4.ps1",
    "README_SUBMISSION.md"
]

print("Copying files to staging directory...")

# Copy files
for f in include_files:
    src_path = base_dir / f
    dest_path = staging_dir / f
    if src_path.exists():
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path)
    else:
        print(f"Warning: File missing {f}")
        
# Copy directories
for d in include_dirs:
    src_d_path = base_dir / d
    dest_d_path = staging_dir / d
    if src_d_path.exists() and src_d_path.is_dir():
        for root, _, files in os.walk(src_d_path):
            if "__pycache__" in root or ".pytest_cache" in root or ".eval_cache" in root:
                continue
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(base_dir)
                dest_file_path = staging_dir / rel_path
                dest_file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_file_path)
    else:
        print(f"Warning: Directory missing {d}")

print("Zipping the staging directory...")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(staging_dir):
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(staging_dir)
            zf.write(file_path, arcname=f"aurabeam_source_code/{rel_path}")

print(f"Done! Package saved to: {zip_path}")
print(f"A staging copy is available at: {staging_dir}")
