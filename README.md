# Hercules Experiment Framework

A lightweight toolkit for running Python experiment sweeps on the Hercules HPC cluster (CICA, Seville) — or any SLURM-based cluster.

The framework wraps your existing experiment code without modifying it. You define the parameter sweep in `config.yaml`, write a thin `runner.py` adapter, and the framework handles job submission, monitoring, and LaTeX table generation.

---

## The idea in three lines

```bash
python core/manager.py   # [R] generates SLURM command files from config.yaml
                         # [F] submits all phases as array jobs with SLURM deps
                         # [T] generates LaTeX tables from results CSVs
```

That is the entire workflow. Your experiment script does not change.

---

## What is in this repository

```
hercules-framework/
├── core/
│   ├── manager.py          # Interactive HUB — the main entry point
│   ├── slurm_generic.sh    # SLURM array template (Hercules-compatible)
│   ├── generate_tables.py  # LaTeX table generator driven by config.yaml
│   └── deploy.sh           # rsync helper to sync your project to Hercules
├── templates/
│   ├── config.yaml         # Annotated configuration template
│   └── runner.py           # Runner template with two sections to adapt
├── examples/
│   ├── ml-classification/  # PyTorch CIFAR-10 sweep example
│   └── qml-vqc/            # PennyLane VQC sweep example
└── docs/
    ├── hercules-setup.md   # SSH, conda, partitions, common errors
    ├── tutorial.md         # Step-by-step: from script to running on Hercules
    └── troubleshooting.md  # Error reference
```

The `core/` files are meant to be copied into your project unchanged. The only files you write are `config.yaml` and `runner.py`.

---

## Quickstart

### 1. Copy the framework into your project

```bash
cp -r hercules-framework/core/ my_project/core/
cp hercules-framework/templates/config.yaml my_project/config.yaml
cp hercules-framework/templates/runner.py my_project/runner.py
```

### 2. Adapt two sections in runner.py

Open `runner.py` and find the two sections marked `ADAPT THIS`:

- **`iter_runs(cfg)`** — yields one dict per experiment combination (model, seed, etc.)
- **`execute_run(run_spec, cfg)`** — calls your experiment and saves results to CSV

Everything else in `runner.py` handles argument parsing, SLURM command export, and resumability. You do not need to touch it.

### 3. Fill in config.yaml

Define your parameter sweep, phases, and LaTeX labels. The full template with inline documentation is in `templates/config.yaml`.

### 4. Test locally

```bash
cd my_project
python runner.py --dry-run           # verify planned runs
python runner.py --model resnet --seed 42   # run one experiment
```

### 5. Deploy and launch on Hercules

```bash
# Edit HERCULES_USER and REMOTE_DIR in core/deploy.sh, then:
bash core/deploy.sh

# SSH in, create the conda environment once:
ssh your_user@hercules.spc.cica.es
cd ~/my_project
module load Miniconda3
conda create -n experiment python=3.10 -y
source activate experiment
pip install -r requirements.txt

# Launch the HUB:
python core/manager.py
# [R] → [F] → wait → [T]
```

---

## How phases work

A phase is a named subset of your parameter sweep submitted as a SLURM array job.
Phases are defined in `config.yaml`:

```yaml
phases:
  - id: "1"
    name: "baseline"
    file: "cmds_1_baseline.txt"
    description: "Baseline models"
    filters:
      noise: false          # only runs where noise=false

  - id: "2"
    name: "noisy"
    file: "cmds_2_noisy.txt"
    description: "Noisy variants"
    filters:
      noise: true
```

When you press `[F]` in the HUB, phases are submitted with sequential SLURM dependencies: Phase 2 will not start until Phase 1 completes successfully. Individual phases can also be submitted independently with `[1]`, `[2]`, etc.

---

## Hercules-specific notes

- Partition for CPU jobs: `standard` (not `cpu` — that partition does not exist)
- Conda activation: `source activate <env>` (not `conda activate`)
- Miniconda path: `/lustre/software/easybuild/common/software/Miniconda3/4.9.2`
- Always use relative paths in your code — absolute paths to `/home/username/` break inside SLURM jobs
- Check `.err` files when a job fails, not `.out`

Full setup guide: [docs/hercules-setup.md](docs/hercules-setup.md)

---

## Generating LaTeX tables

Once your results are in `results/*/`, press `[T]` in the HUB (or run `python core/generate_tables.py`).

Tables are defined entirely in `config.yaml`:

```yaml
tables:
  - name: "tab_main"
    caption: "Test accuracy across models."
    label: "tab:main"
    rows: "model"
    cols: "noise"
    metrics:
      - column: "accuracy"
        label: "Acc~(\\%)"
        pct: true
```

The generator groups results by `rows` and `cols`, computes mean ± std over seeds, and writes a `.tex` file ready to include in your paper.

---

## Real usage

This framework was built and used for the following papers:

- [danimap27/qtl-experiments](https://github.com/danimap27/qtl-experiments) — Hybrid Classical-Quantum Transfer Learning, CMES 2026
- [danimap27/cross-domain-qcl](https://github.com/danimap27/cross-domain-qcl) — Cross-Domain QCL, QUANTICS 2026

---

## Requirements

The core framework only needs PyYAML and (optionally) pandas:

```
pyyaml>=6.0
pandas>=2.0      # optional, for richer monitoring output
```

Your experiment code has its own requirements.

---

## Documentation

- [Hercules setup guide](docs/hercules-setup.md) — access, conda, partitions, monitoring
- [Tutorial](docs/tutorial.md) — step-by-step from script to running on Hercules
- [Troubleshooting](docs/troubleshooting.md) — error reference
