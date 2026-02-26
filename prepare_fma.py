"""
Convert a directory of MP3 files into WAV files for MiniShazam.

This script mirrors the input directory structure under an output directory
and converts each MP3 to mono 44.1 kHz 16-bit WAV using ffmpeg.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from typing import List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare FMA/audio dataset for fingerprinting.")
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing MP3 files (recursive).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where converted WAV files will be written.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Limit number of files converted (0 means no limit).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip conversion if destination WAV already exists.",
    )
    return parser.parse_args()


def find_mp3_files(input_dir: str) -> List[str]:
    files: List[str] = []
    for root, _, names in os.walk(input_dir):
        for name in names:
            if name.lower().endswith(".mp3"):
                files.append(os.path.join(root, name))
    return sorted(files)


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is required but not found on PATH. Install ffmpeg and retry."
        )


def convert_one(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        src,
        "-ac",
        "1",
        "-ar",
        "44100",
        "-sample_fmt",
        "s16",
        dst,
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    input_dir = os.path.abspath(args.input_dir)
    output_dir = os.path.abspath(args.output_dir)

    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    ensure_ffmpeg()
    mp3_files = find_mp3_files(input_dir)
    if not mp3_files:
        raise RuntimeError(f"No .mp3 files found under: {input_dir}")

    if args.max_files > 0:
        mp3_files = mp3_files[:args.max_files]

    print(f"Found {len(mp3_files)} MP3 files to process.", flush=True)
    converted = 0
    skipped = 0
    failed = 0

    for i, src in enumerate(mp3_files, start=1):
        rel = os.path.relpath(src, input_dir)
        dst_rel = os.path.splitext(rel)[0] + ".wav"
        dst = os.path.join(output_dir, dst_rel)

        if args.skip_existing and os.path.exists(dst):
            skipped += 1
            print(f"[{i}/{len(mp3_files)}] skip {dst_rel}", flush=True)
            continue

        try:
            convert_one(src, dst)
            converted += 1
            print(f"[{i}/{len(mp3_files)}] ok   {dst_rel}", flush=True)
        except subprocess.CalledProcessError:
            failed += 1
            print(f"[{i}/{len(mp3_files)}] fail {rel}", flush=True)

    print("Done.")
    print(f"Converted: {converted}")
    print(f"Skipped:   {skipped}")
    print(f"Failed:    {failed}")


if __name__ == "__main__":
    main()
