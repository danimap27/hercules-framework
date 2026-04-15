"""
manager.py — Generic Experiment HUB for Hercules HPC.

Reads all experiment configuration from config.yaml.
Compatible with any project that uses runner.py + slurm_generic.sh.

Usage:
    python core/manager.py                      # uses config.yaml in cwd
    python core/manager.py --config my_cfg.yaml
"""

import os
import sys
import subprocess
import glob
import time
from pathlib import Path
from typing import Optional

import yaml

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header(name: str):
    w = 70
    print("=" * w)
    print(f"{'HERCULES HUB — ' + name.upper():^{w}}")
    print("=" * w)


def run(cmd: str, capture: bool = False):
    try:
        if capture:
            r = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            return r.stdout.strip()
        subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] {e}")
        return None


def count_lines(path: str) -> int:
    if not os.path.exists(path):
        return 0
    for enc in ["utf-8-sig", "utf-16", "latin1"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return sum(1 for l in f if l.strip())
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 0


# ── Actions ────────────────────────────────────────────────────────────────────

def do_refresh(config_path: str, cfg: dict):
    print(f"\n[INFO] Generating command files via runner.py...")
    ok = run(f"python runner.py --config {config_path} --export-commands")
    if ok:
        print("[OK] Done.")
        for p in cfg.get("phases", []):
            n = count_lines(p["file"])
            print(f"  [{p['id']}] {p['description']}: {n} tasks")
    else:
        print("[FAIL] Check runner.py for errors.")
    input("\nEnter to return...")


def do_submit(phase: dict, dependency_id: Optional[str] = None,
              slurm_sh: str = "core/slurm_generic.sh",
              conda_env: str = "experiment") -> Optional[str]:
    n = count_lines(phase["file"])
    if n == 0:
        print(f"\n[WARN] {phase['file']} is empty. Run [R] first.")
        return None
    dep = f"--dependency=afterok:{dependency_id}" if dependency_id else ""
    name = f"{phase['id']}_{phase['name']}"
    cmd = (
        f"sbatch --parsable --job-name='{name}' "
        f"--array=1-{n}%30 {dep} "
        f"--export=CMD_FILE={phase['file']},CONDA_ENV={conda_env} "
        f"{slurm_sh}"
    )
    print(f"\n[SUBMIT] {phase['description']} ({n} tasks)...")
    job_id = run(cmd, capture=True)
    if job_id:
        print(f"[OK] Job ID: {job_id}")
    return job_id


def do_full_pipeline(cfg: dict, slurm_sh: str, conda_env: str):
    phases = cfg.get("phases", [])
    print(f"\n[PIPELINE] Submitting {len(phases)} phases sequentially...")
    prev, ids = None, []
    for p in phases:
        jid = do_submit(p, prev, slurm_sh, conda_env)
        ids.append(jid or "?")
        if jid:
            prev = jid
    print(f"\n[OK] Chain: {' -> '.join(ids)}")
    input("\nEnter to return...")


def do_monitor(cfg: dict):
    results_dir = cfg.get("output_dir", "./results")
    expected = cfg.get("expected_runs", 0)
    pattern = os.path.join(results_dir, "*", "*.csv")
    files = glob.glob(pattern)

    completed = 0
    print(f"\n[MONITOR] {results_dir}/")

    if HAS_PANDAS and files:
        try:
            dfs = [pd.read_csv(f) for f in files]
            df = pd.concat(dfs, ignore_index=True)
            id_col = next((c for c in ["run_id", "id"] if c in df.columns), None)
            completed = len(df.drop_duplicates(subset=[id_col])) if id_col else len(df)
            print(f"\n  Unique runs completed : {completed}")

            # Show per-group breakdown if group_by is defined
            group_cols = cfg.get("results", {}).get("group_by", [])
            metrics = cfg.get("results", {}).get("metrics", [])
            if group_cols and metrics:
                cols = [c for c in group_cols + metrics if c in df.columns]
                if cols:
                    print(f"\n  Summary ({', '.join(group_cols)}):")
                    print(df[cols].groupby(group_cols).mean().to_string())
        except Exception as e:
            print(f"  [WARN] {e}")
            completed = len(files)
    else:
        completed = len(files)
        print(f"  CSV files found: {completed}")

    pct = completed / expected * 100 if expected > 0 else 0.0
    print(f"\n  Progress: {pct:.1f}%  ({completed}/{expected})")

    print("\n  --- Active SLURM jobs ---")
    out = run("squeue -u $USER --format='%.10i %.9P %.40j %.8T %.10M' 2>/dev/null", capture=True)
    print(out or "  No active jobs or squeue not available.")
    input("\nEnter to return...")


def do_tables(config_path: str):
    print("\n[TABLES] Running generate_tables.py...")
    run(f"python core/generate_tables.py --config {config_path}")
    input("\nEnter to return...")


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    name = cfg.get("experiment_name", "experiment")
    phases = cfg.get("phases", [])
    slurm_sh = cfg.get("slurm_script", "core/slurm_generic.sh")
    conda_env = cfg.get("conda_env", "experiment")

    os.makedirs("logs", exist_ok=True)
    os.makedirs(cfg.get("output_dir", "./results"), exist_ok=True)

    while True:
        clear()
        header(name)
        print()
        print("  [R]  Refresh command files from config.yaml")
        print()
        for p in phases:
            n = count_lines(p["file"])
            status = f"{n} tasks" if n > 0 else "empty — run [R]"
            print(f"  [{p['id']}]  {p['description']}  ({status})")
        print()
        print("  [F]  Launch FULL PIPELINE (all phases, sequential deps)")
        print("  [M]  Monitor progress")
        print("  [T]  Generate LaTeX tables")
        print("  [X]  Exit")
        print("-" * 70)

        c = input("Option: ").strip().upper()

        if c == "R":
            do_refresh(args.config, cfg)
        elif c == "F":
            do_full_pipeline(cfg, slurm_sh, conda_env)
        elif c == "M":
            do_monitor(cfg)
        elif c == "T":
            do_tables(args.config)
        elif c == "X":
            print("\nDone.\n")
            break
        elif c in {p["id"] for p in phases}:
            p = next(ph for ph in phases if ph["id"] == c)
            do_submit(p, slurm_sh=slurm_sh, conda_env=conda_env)
            input("\nEnter to return...")
        else:
            print("Unknown option.")
            time.sleep(1)


if __name__ == "__main__":
    main()
