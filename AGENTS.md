# Shazam App AGENTS

## Purpose

Python MiniShazam prototype: fingerprint tracks, build an index, and identify songs from mic/query clips.

## Core Files

- Fingerprinting engine: `fingerprint.py`
- Build DB: `build_db.py`
- Desktop app: `app.py`
- Dataset prep (MP3 -> WAV): `prepare_fma.py`
- Batch evaluation: `evaluate_dataset.py`

## Typical Workflow

1. Create/activate `.venv`, install `requirements.txt`.
2. Convert dataset audio to WAV with `prepare_fma.py`.
3. Build fingerprint database with `build_db.py`.
4. Run app (`app.py`) or benchmark (`evaluate_dataset.py`).

## Dataset Guidance

- Primary public dataset target: FMA small.
- Current project state from sessions: user paused integration while downloading `fma_small`; resume once local dataset path is ready.
- Keep dataset artifacts under `data/` and avoid committing large raw audio files.

## Run Examples

- `python prepare_fma.py --input-dir /abs/path/fma_small --output-dir /abs/path/fma_wav --max-files 500 --skip-existing`
- `python build_db.py --music-dir /abs/path/fma_wav --output /abs/path/fma_fingerprints.pkl`
- `python app.py --db-path /abs/path/fma_fingerprints.pkl`
- `python evaluate_dataset.py --music-dir /abs/path/fma_wav --max-tracks 200 --clip-seconds 5 --min-score 5`
