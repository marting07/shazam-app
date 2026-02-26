"""
build_db.py
===========

This script builds a fingerprint database from a collection of WAV files
stored in the ``music_db`` directory.  It uses the ``FingerprintDB``
class defined in ``fingerprint.py`` to compute constellation maps and
hashes for each track.

Run this script from the repository root (or adjust the paths
accordingly).  It will scan ``music_db`` for all ``.wav`` files,
fingerprint them, and save the resulting database to
``music_db/fingerprints.pkl``.

Example:

    python build_db.py

The synthetic songs distributed with this project can be used to
populate the database.  You can replace or augment them with your own
music files if you prefer.
"""

import argparse
import os
from fingerprint import FingerprintDB


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fingerprint database from audio files."
    )
    parser.add_argument(
        "--music-dir",
        default=os.path.join(os.getcwd(), "music_db"),
        help="Directory to scan for .wav files (recursively).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output .pkl path. Defaults to <music-dir>/fingerprints.pkl.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    base_dir = os.path.abspath(args.music_dir)
    out_path = os.path.abspath(args.output) if args.output else os.path.join(base_dir, "fingerprints.pkl")
    if not os.path.isdir(base_dir):
        raise FileNotFoundError(f"Music directory not found: {base_dir}")

    db = FingerprintDB()
    wav_files = []
    for root, _, files in os.walk(base_dir):
        for fname in files:
            if fname.lower().endswith(".wav"):
                wav_files.append(os.path.join(root, fname))

    if not wav_files:
        raise RuntimeError(f"No .wav files found under: {base_dir}")

    print(f"Found {len(wav_files)} WAV files in {base_dir}", flush=True)
    for path in sorted(wav_files):
        rel_path = os.path.relpath(path, base_dir)
        title = os.path.splitext(os.path.basename(path))[0]
        metadata = {"title": title, "filename": rel_path}
        print(f"Adding {rel_path} ...", flush=True)
        db.add_track(path, metadata)

    print(f"Saving fingerprint database to {out_path}", flush=True)
    db.save(out_path)


if __name__ == "__main__":
    main()
