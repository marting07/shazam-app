"""
fingerprint.py
================

This module implements a simple audio fingerprinting system inspired by
the Shazam algorithm.  The implementation follows the high‑level
description in Avery Li‑Chun Wang's paper on Shazam's industrial
strength audio search algorithm【799623276281538†L130-L145】【799623276281538†L193-L204】.
It does not depend on any specialised audio fingerprinting libraries.

The core idea is to transform audio into a constellation map of
time–frequency peaks, then generate robust hash tokens by pairing
these peaks.  Each hash encodes two frequencies and the time
difference between them【799623276281538†L193-L204】.  When querying, matching
hashes between an unknown sample and a database of known tracks
produce a scatterplot of time offsets; a significant cluster of
offsets implies a match【799623276281538†L280-L338】.

Usage:

  from fingerprint import FingerprintDB

  db = FingerprintDB()
  db.add_track("/path/to/song.wav", metadata={...})
  db.save("fingerprints.pkl")

  # later, load the database and recognise a sample
  db = FingerprintDB.load("fingerprints.pkl")
  track_id, score = db.recognise("/path/to/sample.wav")
  print(db.metadata[track_id], score)

This code is designed to be educational rather than maximally
optimised.  It trades performance for clarity and readability.
"""

from __future__ import annotations

import os
import pickle
import numpy as np
from scipy.io import wavfile
from scipy.signal import stft
from scipy.ndimage import maximum_filter, generate_binary_structure, binary_erosion


def _compute_constellation_map(
    audio: np.ndarray,
    sr: int,
    window_size: int = 4096,
    hop_length: int = 512,
    fan_value: int = 10,
    amp_min: float = -50
) -> np.ndarray:
    """
    Compute a sparse constellation map of spectrogram peaks.

    Parameters
    ----------
    audio : np.ndarray
        1‑D numpy array containing the mono audio signal.
    sr : int
        Sample rate of the audio signal.
    window_size : int
        Size of the FFT window for the short‑time Fourier transform.
    hop_length : int
        Hop length between successive FFT windows.
    fan_value : int
        Unused here but kept for API compatibility; pairing uses this later.
    amp_min : float
        Minimum amplitude (in dB) for a peak to be considered.

    Returns
    -------
    peaks : np.ndarray of shape (N, 2)
        Array of time‑frequency peak coordinates.  Each row is
        (time_index, frequency_index).
    """
    # Compute the magnitude spectrogram
    _, _, Zxx = stft(audio, fs=sr, nperseg=window_size, noverlap=window_size - hop_length)
    magnitude = np.abs(Zxx)
    # Convert to decibels
    mags_db = 20 * np.log10(magnitude + 1e-10)

    # Use a neighbourhood structure to detect local maxima.  A peak is a point
    # that is greater than all other points in its neighbourhood.  This
    # approach follows the description of selecting spectrogram peaks as
    # candidate features【799623276281538†L130-L145】.
    struct = generate_binary_structure(2, 2)
    neighbourhood = maximum_filter(mags_db, footprint=struct) == mags_db
    # Apply a threshold to remove low‑energy points
    threshold = mags_db > amp_min
    local_max = neighbourhood & threshold
    # Erode the peak mask to sharpen the peaks
    eroded = binary_erosion(local_max, structure=struct)
    peaks_mask = local_max ^ eroded

    # Get peak indices
    freq_idx, time_idx = np.where(peaks_mask)
    peaks = np.stack((time_idx, freq_idx), axis=-1)
    return peaks


def _generate_hashes(
    peaks: np.ndarray,
    fan_value: int = 10,
    min_time_delta: int = 0,
    max_time_delta: int = 200
) -> list[tuple[int, int]]:
    """
    Generate hash tokens from a constellation map.

    For each peak (anchor point), pair it with up to `fan_value`
    neighbouring peaks ahead in time within [min_time_delta, max_time_delta] bins.
    Each pair yields a hash composed of (f1, f2, dt), where f1 and f2 are
    frequency bin indices and dt is the difference in time bins【799623276281538†L193-L204】.

    Parameters
    ----------
    peaks : np.ndarray of shape (N, 2)
        Sorted array of (time_index, frequency_index) pairs.
    fan_value : int
        Number of pairs to form for each anchor point.
    min_time_delta : int
        Minimum time difference between anchor and target peaks (in bins).
    max_time_delta : int
        Maximum time difference between anchor and target peaks (in bins).

    Returns
    -------
    hashes : list of tuples (hash_val, offset)
        Each element contains a 32‑bit integer hash and the time index of
        the anchor peak.  The offset is used later to align matches.
    """
    # Sort peaks by time to ensure monotonic order for pairing
    peaks = peaks[np.argsort(peaks[:, 0])]
    hashes: list[tuple[int, int]] = []
    # For each anchor point, pair with subsequent points within the target zone
    for i in range(len(peaks)):
        anchor_time, anchor_freq = peaks[i]
        # Consider candidate points ahead in time
        for j in range(1, fan_value + 1):
            if i + j >= len(peaks):
                break
            target_time, target_freq = peaks[i + j]
            dt = target_time - anchor_time
            if dt < min_time_delta:
                continue
            if dt > max_time_delta:
                break
            # Combine the frequencies and time delta into a single integer.
            # Use 10 bits for each frequency and 12 bits for dt (up to 4096).  This
            # packing yields a 32‑bit hash that uniquely identifies the pair.
            hash_val = (anchor_freq & 0x3FF) << 22 | (target_freq & 0x3FF) << 12 | (dt & 0xFFF)
            hashes.append((hash_val, anchor_time))
    return hashes


class FingerprintDB:
    """
    Simple in‑memory fingerprint database.

    The database holds a mapping from hash tokens to lists of (track_id, offset)
    pairs and a metadata dictionary containing user‑provided metadata for each
    track.  When adding a track, its constellation map and hashes are computed
    and inserted into the index.  During recognition, the index is queried
    against an unknown sample to accumulate offset votes per track as described
    in the Shazam paper【799623276281538†L280-L338】.
    """

    def __init__(self):
        self.hash_table: dict[int, list[tuple[int, int]]] = {}
        self.metadata: dict[int, dict] = {}
        self._next_track_id = 0

    def add_track(self, filepath: str, metadata: dict | None = None) -> int:
        """
        Add an audio track to the fingerprint database.

        Parameters
        ----------
        filepath : str
            Path to the audio file (WAV format) to add.
        metadata : dict, optional
            Arbitrary metadata about the track (e.g. title, artist, album).  If
            omitted, a default metadata dict containing the filename will be
            stored.

        Returns
        -------
        track_id : int
            Internal identifier assigned to the new track.
        """
        track_id = self._next_track_id
        self._next_track_id += 1
        # Read audio file
        sr, audio = wavfile.read(filepath)
        # Convert stereo to mono if necessary
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        # Normalise audio to floating point
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio = audio.astype(np.float32) / 2147483648.0
        else:
            audio = audio.astype(np.float32)
        # Compute constellation map
        peaks = _compute_constellation_map(audio, sr)
        # Generate hashes
        hashes = _generate_hashes(peaks)
        # Insert into hash table
        for h, offset in hashes:
            self.hash_table.setdefault(h, []).append((track_id, offset))
        # Store metadata
        if metadata is None:
            metadata = {"title": os.path.basename(filepath)}
        self.metadata[track_id] = metadata
        return track_id

    def recognise(self, filepath: str) -> tuple[int | None, int]:
        """
        Recognise an unknown audio sample.

        This function fingerprints the sample and queries the database to
        accumulate offset votes per candidate track.  The track with the
        largest cluster of consistent offsets is returned along with its score
        (the number of matching hashes in the largest offset bin)【799623276281538†L280-L338】.

        Parameters
        ----------
        filepath : str
            Path to the audio file (WAV format) to identify.

        Returns
        -------
        track_id : int or None
            The identified track ID, or None if no significant match was found.
        best_score : int
            The highest number of aligned matching hashes for the identified track.
        """
        # Read audio file
        sr, audio = wavfile.read(filepath)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype == np.int32:
            audio = audio.astype(np.float32) / 2147483648.0
        else:
            audio = audio.astype(np.float32)
        peaks = _compute_constellation_map(audio, sr)
        hashes = _generate_hashes(peaks)
        # Accumulate offset votes per track
        votes: dict[int, dict[int, int]] = {}
        for h, offset in hashes:
            matches = self.hash_table.get(h)
            if not matches:
                continue
            for track_id, db_offset in matches:
                dt = db_offset - offset
                votes.setdefault(track_id, {}).setdefault(dt, 0)
                votes[track_id][dt] += 1
        # Find the best matching track
        best_track = None
        best_score = 0
        for track_id, offsets in votes.items():
            # Score is the largest cluster size (number of matching hashes) in the histogram
            score = max(offsets.values())
            if score > best_score:
                best_score = score
                best_track = track_id
        return best_track, best_score

    def save(self, filename: str) -> None:
        """
        Save the fingerprint database to disk using pickle.
        """
        with open(filename, "wb") as f:
            pickle.dump({
                'hash_table': self.hash_table,
                'metadata': self.metadata,
                '_next_track_id': self._next_track_id,
            }, f)

    @classmethod
    def load(cls, filename: str) -> FingerprintDB:
        """
        Load a fingerprint database from disk.
        """
        with open(filename, "rb") as f:
            data = pickle.load(f)
        obj = cls()
        obj.hash_table = data['hash_table']
        obj.metadata = data['metadata']
        obj._next_track_id = data['_next_track_id']
        return obj