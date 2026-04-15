# Hercules Setup Guide

Hercules is the HPC cluster managed by CICA (Centro de Informática Científica de Andalucía).
This document covers everything needed to go from zero to running jobs.

---

## 1. Getting access

Request access through your institution's CICA contact. For UPO, the request goes through the research group PI. You will need to specify:

- Software requirements (Python, CUDA if GPU is needed)
- Approximate compute needs (CPU cores, RAM, wall time per job)
- Associated research project or grant

---

## 2. SSH access

```bash
ssh your_user@hercules.spc.cica.es
```

The login node is for file transfer and job submission only. Running computation on the login node will get your session killed. Always use `salloc` or `sbatch` for any real work.

Interactive session on a compute node:

```bash
salloc --mem=16G -c 4 -t 06:00:00 srun --pty /bin/bash -i
```

---

## 3. Conda setup

Miniconda is available as a module. Load it once per session:

```bash
module load Miniconda3
```

Create your environment (first time only):

```bash
conda create -n experiment python=3.10 -y
```

**Important:** On Hercules, use `source activate` instead of `conda activate`:

```bash
source activate experiment
pip install -r requirements.txt
```

The `conda activate` command fails unless you have run `conda init` in your shell profile, which requires restarting the session. `source activate` always works.

---

## 4. Partitions

| Partition | Use | Time limit |
|---|---|---|
| `standard` | CPU jobs, general purpose | None |
| `gpu` | GPU jobs | 30 days |

The partition named `cpu` does not exist. Using `--partition=cpu` will fail with an error. Always use `standard` for CPU jobs.

---

## 5. File system

Your home directory has limited quota. For large datasets and results, use the scratch or lustre filesystem if available:

```
/lustre/home/your_user/   # persistent storage (check quota)
/scratch/your_user/       # fast temporary storage
```

Always use relative paths in your code. Hardcoding `/home/quantum-nas/...` will break on other machines or if your home directory path changes.

---

## 6. Monitoring jobs

```bash
squeue -u $USER                          # list your active jobs
scancel <job_id>                         # cancel a job
tail -f logs/your_job_12345_1.out        # follow a running job's output
```

Web portal (login required):
`https://ood-hercules.spc.cica.es/pun/sys/hercules-job-performance`

---

## 7. Common errors

| Error | Cause | Fix |
|---|---|---|
| `CondaError: Run conda init` | Using `conda activate` | Use `source activate <env>` |
| `invalid partition specified: cpu` | Partition does not exist | Use `--partition=standard` |
| `PermissionError: /home/username/...` | Hardcoded absolute path | Use relative paths in code |
| Job finishes in under 1 minute | Script crash | Check `.err` file, not `.out` |
| `ModuleNotFoundError` | Package not installed in env | `pip install -r requirements.txt` inside activated env |

---

## 8. Email notifications

Add to your SLURM script to get notified on job failure:

```bash
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=your_email@institution.es
```
