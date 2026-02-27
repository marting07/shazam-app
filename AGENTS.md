# Shazam App AGENTS

## Purpose

Python MiniShazam prototype: fingerprint tracks, build an index, and identify songs from mic/query clips.

## Core Files

- Fingerprinting engine: `fingerprint.py`
- Build DB: `build_db.py`
- Desktop app: `app.py`
- Dataset prep (MP3 -> WAV): `prepare_fma.py`
- Batch evaluation: `evaluate_dataset.py`
- Detached long-run helper: `data/results/run_999_overnight.sh`

## Dataset State

- FMA small has been downloaded and extracted under `data/public/fma_small/`.
- Working WAV subset flow is under `data/subsets/` (for example `fma_small_1000_wav`).
- Keep all large data outputs in `data/` and out of git (`.gitignore` already covers this).

## Typical Workflow

1. Create/activate `.venv`, install `requirements.txt`.
2. Convert MP3 dataset audio to WAV with `prepare_fma.py`.
3. Build fingerprint database with `build_db.py`.
4. Run evaluation with `evaluate_dataset.py`.
5. Optionally run detached overnight benchmark script for 999-track sweeps.

## Run Examples

- `python prepare_fma.py --input-dir /abs/path/fma_small --output-dir /abs/path/fma_wav --max-files 1000 --skip-existing`
- `python build_db.py --music-dir /abs/path/fma_wav --output data/db/fma_small_1000.pkl`
- `python app.py --db-path data/db/fma_small_1000.pkl`
- `python evaluate_dataset.py --music-dir /abs/path/fma_wav --max-tracks 500 --clip-seconds 5 --min-score 5`
- `nohup sh data/results/run_999_overnight.sh > data/results/nohup_999.out 2>&1 &`

## Workflow Decisions

- Use `data/results/*.txt` for benchmark summaries and `data/results/*.log` for long-run logs.
- PID tracking for detached runs is stored in `data/results/fma_small_999_overnight.pid`.
- Current benchmark progression is 300 -> 500 -> 999 tracks; keep command lines reproducible and saved in `data/results/`.
