# Tutorial: Adapting Your Code to Run on Hercules

This tutorial walks through the complete process of taking an existing Python experiment
and running it as a SLURM array job on Hercules with the framework.

The framework has one core idea: **your experiment script does not change**.
You write a thin `runner.py` wrapper that generates all parameter combinations
and calls your script for each one. The framework handles the rest.

---

## What you need before starting

- A Python script that runs one experiment (e.g., `python my_experiment.py --lr 0.01 --seed 42`)
- A list of parameters you want to sweep over
- SSH access to Hercules

---

## Step 1 — Make your script accept CLI arguments

Your experiment script should accept all variable parameters as CLI arguments.
If it already does, skip this step.

Before:
```python
# my_experiment.py
lr = 0.001       # hardcoded
seed = 42        # hardcoded
model = "resnet" # hardcoded
run_training(lr, seed, model)
```

After:
```python
# my_experiment.py
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--lr",    type=float, default=0.001)
ap.add_argument("--seed",  type=int,   default=42)
ap.add_argument("--model", default="resnet")
args = ap.parse_args()
run_training(args.lr, args.seed, args.model)
```

Your script should also save results to a CSV file so `generate_tables.py` can pick them up:

```python
import csv, os, time
from pathlib import Path

run_id = f"{args.model}__lr{args.lr}__s{args.seed}"
out_dir = Path("results") / run_id
out_dir.mkdir(parents=True, exist_ok=True)

with open(out_dir / "results.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=["run_id", "accuracy", "loss", "timestamp"])
    writer.writeheader()
    writer.writerow({
        "run_id": run_id,
        "accuracy": accuracy,
        "loss": loss,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
```

---

## Step 2 — Set up the project structure

Copy the framework files into your project:

```
my_project/
├── my_experiment.py        # your code (unchanged)
├── runner.py               # copy from templates/runner.py and adapt
├── config.yaml             # copy from templates/config.yaml and fill in
├── core/
│   ├── manager.py          # copy as-is from core/
│   ├── slurm_generic.sh    # copy as-is from core/
│   ├── generate_tables.py  # copy as-is from core/
│   └── deploy.sh           # copy as-is from core/
├── results/                # created automatically
├── logs/                   # created automatically
└── requirements.txt
```

---

## Step 3 — Write config.yaml

Define your parameter sweep and phases.

```yaml
experiment_name: "my_experiment"
conda_env: "my_env"
output_dir: "./results"

seeds: [0, 42, 123, 456, 789]

models:
  - name: "resnet18"
  - name: "mobilenetv2"

learning_rates: [0.001, 0.01]

phases:
  - id: "1"
    name: "resnet_sweep"
    file: "cmds_1_resnet.txt"
    description: "ResNet-18 LR sweep"
    filters:
      model: "resnet18"

  - id: "2"
    name: "mobilenet_sweep"
    file: "cmds_2_mobilenet.txt"
    description: "MobileNetV2 LR sweep"
    filters:
      model: "mobilenetv2"

expected_runs: 20   # 2 models × 2 lr × 5 seeds

labels:
  model:
    resnet18: "ResNet-18"
    mobilenetv2: "MobileNet-V2"

tables:
  - name: "tab_main"
    caption: "Test accuracy and loss across models."
    label: "tab:main"
    rows: "model"
    cols: "lr"
    metrics:
      - column: "accuracy"
        label: "Acc~(\\%)"
        pct: true
      - column: "loss"
        label: "Loss"
        pct: false
```

---

## Step 4 — Write runner.py

Copy `templates/runner.py` and adapt the two marked sections.

Section 1 — `iter_runs()`: yields one dict per experiment combination.
Section 2 — `execute_run()`: calls your experiment and saves results.

```python
def iter_runs(cfg):
    for model in [m["name"] for m in cfg["models"]]:
        for lr in cfg["learning_rates"]:
            for seed in cfg["seeds"]:
                run_id = f"{model}__lr{lr}__s{seed}"
                yield {"run_id": run_id, "model": model, "lr": lr, "seed": seed}

def execute_run(run_spec, cfg, machine_id="local"):
    cmd = (
        f"python my_experiment.py "
        f"--model {run_spec['model']} "
        f"--lr {run_spec['lr']} "
        f"--seed {run_spec['seed']}"
    )
    os.system(cmd)
```

Test it locally first:

```bash
python runner.py --dry-run           # shows planned runs without executing
python runner.py --model resnet18 --seed 42  # run one experiment
```

---

## Step 5 — Sync to Hercules

Edit `HERCULES_USER` and `REMOTE_DIR` in `core/deploy.sh`, then:

```bash
bash core/deploy.sh
```

This rsyncs everything except `data/raw/`, `results/`, and `logs/`.

---

## Step 6 — Set up the environment on Hercules

SSH in and create the conda environment (first time only):

```bash
ssh your_user@hercules.spc.cica.es
cd ~/my_project
module load Miniconda3
conda create -n my_env python=3.10 -y
source activate my_env
pip install -r requirements.txt
```

---

## Step 7 — Launch with manager.py

```bash
python core/manager.py
```

The interactive menu:

```
[R]  Refresh command files from config.yaml
[1]  Phase 1 — ResNet-18 LR sweep  (10 tasks)
[2]  Phase 2 — MobileNetV2 LR sweep  (10 tasks)
[F]  Launch FULL PIPELINE (all phases, sequential deps)
[M]  Monitor progress
[T]  Generate LaTeX tables
```

Typical workflow:
1. Press `[R]` to generate the command files.
2. Press `[F]` to submit all phases to SLURM.
3. Press `[M]` to watch progress.
4. Press `[T]` to generate tables once progress reaches 100%.

---

## Step 8 — Get results

Tables are written to `paper/tables/`. Each file is a standalone `.tex` table.
Include them in your paper with:

```latex
\input{paper/tables/tab_main.tex}
```

Sync results back to your local machine:

```bash
rsync -avz your_user@hercules.spc.cica.es:~/my_project/results/ ./results/
```

Then run `generate_tables.py` locally to review:

```bash
python core/generate_tables.py
```

---

## Tips

- Use `--dry-run` before submitting to verify the command list looks correct.
- Set `expected_runs` in config.yaml so the monitor shows a meaningful percentage.
- Add `--mail-type=FAIL --mail-user=you@inst.es` to `slurm_generic.sh` to get emails on crashes.
- The `[M]` monitor reads any CSV files in `results/*/`. Your CSV column names must match the `metrics:` keys in config.yaml.
- Jobs within a phase run in parallel (up to 30 at a time by default). Phases chain sequentially via SLURM dependencies when using `[F]`.
