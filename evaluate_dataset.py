"""
Evaluate recognition accuracy on a real WAV dataset.

This script builds an in-memory fingerprint index from WAV files and then
queries short excerpts sampled from each track to estimate top-1 accuracy.
"""

from __future__ import annotations

import argparse
import os
import random
import tempfile
from typing import List

import numpy as np
from scipy.io import wavfile
from scipy.io.wavfile import write as wavwrite

from fingerprint import FingerprintDB


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate MiniShazam on a WAV dataset.")
    parser.add_argument(
        "--music-dir",
        required=True,
        help="Directory containing WAV files (recursive scan).",
    )
    parser.add_argument(
        "--clip-seconds",
        type=float,
        default=5.0,
        help="Query clip length in seconds.",
    )
    parser.add_argument(
        "--max-tracks",
        type=int,
        default=100,
        help="Maximum number of tracks to evaluate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic sampling.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=5,
        help="Minimum score considered a valid match.",
    )
    return parser.parse_args()


def list_wav_files(music_dir: str) -> List[str]:
    files: List[str] = []
    for root, _, names in os.walk(music_dir):
        for name in names:
            if name.lower().endswith(".wav"):
                files.append(os.path.join(root, name))
    return sorted(files)


def to_mono_float32(audio: np.ndarray) -> np.ndarray:
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if audio.dtype == np.int16:
        return audio.astype(np.float32) / 32768.0
    if audio.dtype == np.int32:
        return audio.astype(np.float32) / 2147483648.0
    return audio.astype(np.float32)


def make_query_clip(path: str, clip_seconds: float, rng: random.Random) -> str:
    sr, audio = wavfile.read(path)
    audio = to_mono_float32(audio)
    clip_len = max(1, int(sr * clip_seconds))
    if len(audio) <= clip_len:
        clip = audio
    else:
        start = rng.randint(0, len(audio) - clip_len)
        clip = audio[start:start + clip_len]

    clip_i16 = np.int16(np.clip(clip, -1.0, 1.0) * 32767)
    fd, tmp_path = tempfile.mkstemp(prefix="query_", suffix=".wav")
    os.close(fd)
    wavwrite(tmp_path, sr, clip_i16)
    return tmp_path


def main() -> None:
    args = parse_args()
    music_dir = os.path.abspath(args.music_dir)
    rng = random.Random(args.seed)

    if not os.path.isdir(music_dir):
        raise FileNotFoundError(f"Music directory not found: {music_dir}")

    all_files = list_wav_files(music_dir)
    if not all_files:
        raise RuntimeError(f"No .wav files found under: {music_dir}")

    if len(all_files) > args.max_tracks:
        all_files = rng.sample(all_files, args.max_tracks)

    print(f"Building database with {len(all_files)} tracks...", flush=True)
    db = FingerprintDB()
    expected_by_id = {}
    for wav_path in all_files:
        rel = os.path.relpath(wav_path, music_dir)
        track_id = db.add_track(wav_path, {"title": os.path.splitext(os.path.basename(wav_path))[0], "filename": rel})
        expected_by_id[track_id] = wav_path

    print("Running recognition queries...", flush=True)
    attempts = 0
    correct = 0
    rejected = 0
    for track_id, wav_path in expected_by_id.items():
        query_path = make_query_clip(wav_path, args.clip_seconds, rng)
        try:
            predicted_id, score = db.recognise(query_path)
        finally:
            try:
                os.remove(query_path)
            except OSError:
                pass

        attempts += 1
        if predicted_id is None or score < args.min_score:
            rejected += 1
            continue
        if predicted_id == track_id:
            correct += 1

    accuracy = (correct / attempts) * 100.0 if attempts else 0.0
    rejection_rate = (rejected / attempts) * 100.0 if attempts else 0.0
    print(f"Tracks evaluated: {attempts}")
    print(f"Top-1 accuracy: {accuracy:.2f}%")
    print(f"Rejected (score < {args.min_score}): {rejection_rate:.2f}%")


if __name__ == "__main__":
    main()
