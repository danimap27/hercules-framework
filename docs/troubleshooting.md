# Troubleshooting

A reference for errors that appear regularly when running on Hercules.

---

## SLURM errors

**`invalid partition specified: cpu`**
The partition `cpu` does not exist on Hercules. Change `--partition=cpu` to `--partition=standard` in your SLURM script. This is the most common mistake after copying scripts from other clusters.

**Job finishes in under 10 seconds with exit code 1**
The job crashed during setup. Check the `.err` file, not `.out`:
```bash
tail -50 logs/jobname_12345_1.err
```

**`sbatch: error: Batch job submission failed`**
Usually a syntax error in the `#SBATCH` directives. Run `sbatch --test-only your_script.sh` to validate before submitting.

**Array jobs not starting**
Check that `CMD_FILE` is being passed correctly:
```bash
sbatch --array=1-5 --export=CMD_FILE=cmds_1.txt core/slurm_generic.sh
```
If `CMD_FILE` is empty, the job will error immediately.

---

## Conda errors

**`CondaError: Run 'conda init' before 'conda activate'`**
Use `source activate <env>` instead of `conda activate <env>`. Both commands activate the environment, but `source activate` does not require `conda init` to have been run.

**`PackageNotFoundError` or `ImportError` inside a job**
The job is probably using a different conda environment than the one where you installed packages. Check:
```bash
which python   # should show your env path
conda info     # shows active environment
```

**Environment activates locally but not in SLURM**
SLURM jobs do not inherit the interactive shell environment. The SLURM script must explicitly source conda and activate the environment. `slurm_generic.sh` does this automatically.

---

## Path errors

**`FileNotFoundError` or `PermissionError` with a path like `/home/quantum-nas/...`**
Hardcoded absolute paths in your code will fail when the script runs as a different user or in a different home directory. Replace all absolute paths with relative ones:
```python
# Bad
data_path = "/home/quantum-nas/data/dataset.csv"

# Good
data_path = "./data/dataset.csv"
```

**`FileNotFoundError` for data files on Hercules**
Data directories are excluded from `deploy.sh` to avoid syncing large files. Either sync the data separately or download it directly on the cluster:
```bash
rsync -avz ./data/ your_user@hercules.spc.cica.es:~/project/data/
```

---

## Python errors

**`ModuleNotFoundError: No module named 'pennylane'`**
The package is not installed in the active environment. SSH into Hercules, activate the environment, and install:
```bash
source activate experiment
pip install pennylane
```

**Jobs complete but results CSV is empty or missing**
Check that `execute_run()` in `runner.py` is writing to `results/<run_id>/`, not to an absolute path. Also check that the job did not error before reaching the save step (inspect `.err`).

**`UnicodeDecodeError` when reading command files**
Usually caused by Windows line endings (CRLF) in files edited on Windows. Fix with:
```bash
sed -i 's/\r//' cmds_1.txt
```

---

## Performance issues

**Jobs are slow even with 4 CPUs requested**
PennyLane's `default.qubit` uses multiple threads by default. Set `OMP_NUM_THREADS` to match your SLURM allocation:
```bash
export OMP_NUM_THREADS=4
```
Add this to `slurm_generic.sh` before the `eval` line.

**Too many jobs running at once causing cluster slowdown**
The default `--array=1-N%30` limits concurrent jobs to 30. Reduce this number by changing `%30` to a smaller value in `manager.py`'s `do_submit()` function.
