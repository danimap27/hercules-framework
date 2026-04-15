"""
runner.py — TEMPLATE
Copy this file to your project root and adapt the marked sections.

This file does three things:
  1. Generates all experiment combinations from config.yaml (iter_runs).
  2. Exports them as command-line strings for SLURM (--export-commands).
  3. Executes a single run when called with --run-id (from SLURM).

The only part you need to change is execute_run() and iter_runs() to match
your own experiment logic and config structure.
"""

import argparse
import csv
import logging
import os
import sys
import time
from itertools import product
from pathlib import Path

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


# =============================================================================
# SECTION 1 — Run ID and cartesian product
# Adapt iter_runs() to match the dimensions in your config.yaml.
# =============================================================================

def make_run_id(*args) -> str:
    """Build a unique run identifier from parameter values."""
    return "__".join(str(a) for a in args)


def iter_runs(cfg: dict):
    """
    Yield all (param_dict) combinations from config.yaml.

    ADAPT THIS: replace the keys below with your own config sections.
    """
    models = [m["name"] for m in cfg.get("models", [])]
    seeds  = cfg.get("seeds", [0])

    for model, seed in product(models, seeds):
        run_id = make_run_id(model, f"s{seed}")
        yield {
            "run_id": run_id,
            "model": model,
            "seed": seed,
        }


# =============================================================================
# SECTION 2 — Phase filtering
# Matches each run against the phase filters defined in config.yaml.
# You do not need to change this unless your filters use custom logic.
# =============================================================================

def apply_filter(runs: list[dict], phase: dict) -> list[dict]:
    filters = phase.get("filters", {})
    result = []
    for r in runs:
        if all(r.get(k) == v for k, v in filters.items()):
            result.append(r)
    return result


# =============================================================================
# SECTION 3 — Single run execution
# ADAPT THIS: replace the body of execute_run() with your own experiment code.
# The run_spec dict contains all parameter values for this run.
# Save your results to a CSV in results/<run_id>/ so generate_tables.py can read them.
# =============================================================================

def execute_run(run_spec: dict, cfg: dict, machine_id: str = "local"):
    """
    Execute a single experiment run and save results to CSV.

    ADAPT THIS FUNCTION.
    """
    run_id = run_spec["run_id"]
    results_dir = cfg.get("output_dir", "./results")
    run_dir = Path(results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "results.csv"

    # Skip if already done
    if csv_path.exists():
        logger.info(f"[SKIP] {run_id} already completed.")
        return

    logger.info(f"[START] {run_id}")
    t0 = time.time()

    # ── YOUR EXPERIMENT CODE STARTS HERE ──────────────────────────────────────
    # Replace this block with the actual experiment logic.
    # Use run_spec["model"], run_spec["seed"], etc. to access parameters.

    import random
    random.seed(run_spec["seed"])
    accuracy = random.uniform(0.7, 0.95)   # replace with your metric
    loss     = random.uniform(0.1, 0.5)    # replace with your metric

    # ── YOUR EXPERIMENT CODE ENDS HERE ────────────────────────────────────────

    elapsed = time.time() - t0

    row = {
        "run_id":     run_id,
        "model":      run_spec["model"],
        "seed":       run_spec["seed"],
        "accuracy":   accuracy,
        "loss":       loss,
        "train_time": elapsed,
        "machine_id": machine_id,
        "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    write_header = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    logger.info(f"[DONE] {run_id} | acc={accuracy:.4f} | t={elapsed:.1f}s")


# =============================================================================
# SECTION 4 — Command export for SLURM
# No need to change this.
# =============================================================================

def export_commands(runs: list[dict], out_path: str, config_path: str):
    lines = []
    for r in runs:
        cmd = (
            f"python runner.py --config {config_path} --run-id {r['run_id']} "
            + " ".join(f"--{k} {v}" for k, v in r.items() if k != "run_id")
        )
        lines.append(cmd)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    logger.info(f"Exported {len(lines)} commands to {out_path}")


# =============================================================================
# CLI
# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--export-commands", action="store_true")
    ap.add_argument("--machine-id", default="local")
    args = ap.parse_args()

    cfg = load_config(args.config)
    all_runs = list(iter_runs(cfg))

    if args.export_commands:
        for phase in cfg.get("phases", []):
            filtered = apply_filter(all_runs, phase)
            export_commands(filtered, phase["file"], args.config)
        return

    if args.run_id:
        run_spec = next((r for r in all_runs if r["run_id"] == args.run_id), {
            "run_id": args.run_id,
            "model": args.model,
            "seed": args.seed,
        })
        execute_run(run_spec, cfg, args.machine_id)
        return

    runs = all_runs
    if args.model:
        runs = [r for r in runs if r["model"] == args.model]
    if args.seed is not None:
        runs = [r for r in runs if r["seed"] == args.seed]

    logger.info(f"Planned runs: {len(runs)}")
    if args.dry_run:
        for r in runs:
            print(f"  {r['run_id']}")
        return

    for r in runs:
        execute_run(r, cfg, args.machine_id)


if __name__ == "__main__":
    main()
