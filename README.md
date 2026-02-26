# MiniShazam (Python)

A simplified Shazam-style music recognizer built for learning and prototyping.

It fingerprints audio by:
1. Computing spectrogram peak constellations
2. Hashing peak pairs into compact tokens
3. Matching by time-offset vote clustering

## Project Layout

- `fingerprint.py`: core fingerprinting + matching engine
- `build_db.py`: builds a fingerprint index (`.pkl`) from WAV files
- `app.py`: PyQt6 desktop app that records from microphone and identifies a song
- `prepare_fma.py`: converts MP3 dataset files to WAV recursively (ffmpeg)
- `evaluate_dataset.py`: quick benchmark utility for real WAV datasets
- `music_db/`: sample synthetic tracks + generated fingerprint DB

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start (Synthetic Demo)

```bash
python build_db.py
python app.py
```

Press **Start Recording**, play one of the indexed songs, and check the match result.

## Test With Real Music (Public Dataset)

Recommended dataset for first integration: **FMA small** (Free Music Archive).

Why FMA small:
- Public, research-friendly source
- Big enough to stress-test matching quality
- Small enough for local iteration

### Integration Workflow

1. Download FMA small audio locally (MP3 files).
2. Convert MP3 to WAV (16-bit PCM, mono preferred) with `prepare_fma.py`.
3. Build fingerprints from the WAV directory.
4. Run app or run batch evaluation.

Example conversion command (first 500 tracks):

```bash
python prepare_fma.py \
  --input-dir /absolute/path/to/fma_small \
  --output-dir /absolute/path/to/fma_wav \
  --max-files 500 \
  --skip-existing
```

Build DB from any folder (recursive):

```bash
python build_db.py --music-dir /absolute/path/to/fma_wav --output /absolute/path/to/fma_fingerprints.pkl
```

Run desktop app with that database:

```bash
python app.py --db-path /absolute/path/to/fma_fingerprints.pkl
```

## Evaluate Real-Dataset Recognition

`evaluate_dataset.py` builds an in-memory DB, creates random short query clips per track, and reports top-1 accuracy:

```bash
python evaluate_dataset.py --music-dir /absolute/path/to/fma_wav --max-tracks 200 --clip-seconds 5 --min-score 5
```

Outputs:
- `Tracks evaluated`
- `Top-1 accuracy`
- `Rejected` (queries below confidence threshold)

## Integration Assessment (Current Codebase)

Current status:
- Core fingerprint flow is already compatible with real music in WAV format.
- Main blocker is data prep (MP3 -> WAV) and dataset scale/performance.

Expected constraints:
- Fingerprint build time grows roughly linearly with track count.
- Pickled in-memory hash table will become large with bigger datasets.
- Accuracy depends on parameters (`window_size`, `hop_length`, `amp_min`, `fan_value`) and clip quality.

Recommended next improvements:
1. Add persistent/indexed storage (SQLite or key-value) instead of only pickle.
2. Add parallel DB building for large corpora.
3. Calibrate decision threshold using evaluation results before UI-only testing.
