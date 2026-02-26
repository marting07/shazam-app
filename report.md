# Building a Shazam‑like music recogniser

## Overview

This project implements a simplified version of the Shazam music‑recognition system entirely in Python.  It contains:

* **Fingerprinting module (`fingerprint.py`)** – Implements the core audio fingerprinting algorithm described by Avery Li‑Chun Wang for Shazam【799623276281538†L130-L145】【799623276281538†L193-L204】.  It converts audio into a constellation of time‑frequency peaks, hashes pairs of peaks into compact tokens and matches unknown recordings by clustering time‑offset votes【799623276281538†L193-L204】【799623276281538†L280-L338】.
* **Database builder (`build_db.py`)** – Scans a directory of `.wav` files, extracts fingerprints and writes them to a pickled database.
* **Graphical application (`app.py`)** – A PyQt6 desktop app that records audio from a microphone, fingerprints it and identifies the song from the database.

To make the system self‑contained, three synthetic “songs” have been generated (simple mixtures of sine waves).  These stand in for real music during testing.  The code is modular, so real songs (e.g. from the FMA dataset) can be substituted easily.

## Algorithm

### Constellation maps

Shazam’s algorithm begins by converting each track into a **constellation map** of spectrogram peaks.  For each short‑time Fourier transform window, the magnitude spectrum is computed and peaks that are larger than all neighbours in their local region are selected【799623276281538†L130-L145】.  Keeping only the highest‑amplitude peaks makes the representation robust to noise and equalisation【799623276281538†L130-L160】.  The resulting map is a sparse set of 
\((t, f)\) coordinates (time bin, frequency bin).

### Fast combinatorial hashing

Searching directly over constellations would be slow.  Shazam therefore pairs each peak (anchor) with a set of nearby peaks and encodes the frequencies and time difference into a compact 32‑bit hash【799623276281538†L193-L204】.  In our implementation the hash uses 10 bits for each frequency and 12 bits for the time difference.  Pairing increases the entropy of the tokens compared with single peaks, reducing false matches and accelerating the search【799623276281538†L229-L244】.

For each anchor peak we pair it with up to *fan* other peaks that occur shortly after it (up to 200 time bins ahead).  Each pair yields a hash and stores the anchor time as the offset.  In the database these hashes are mapped to track IDs and offsets.

### Searching and scoring

To recognise a query, its constellation map is hashed in the same way.  For every query hash found in the database we retrieve all matching track/offset pairs.  For each candidate track, we accumulate a histogram of *time differences* between the database offset and the query offset.  If the query and database track match, many hashes will align at a common time shift.  Wang’s paper proposes detecting a significant peak in this histogram to declare a match【799623276281538†L280-L338】.  Our implementation returns the track with the largest histogram peak as long as it exceeds a small threshold.

This “astronavigation” approach allows recognition despite heavy noise, compression and partial recordings【799623276281538†L170-L180】【799623276281538†L280-L338】.  The database stores only hashed tokens; the original audio is not required for matching.

## Music database

You need a collection of songs and metadata for fingerprinting.  An excellent choice is the **Free Music Archive (FMA) dataset**, which was designed for music information retrieval tasks.  According to its repository, FMA contains **106 574 tracks** totalling **917 GiB of Creative‑Commons licensed audio** from 16 341 artists and 14 854 albums【646472324112212†L319-L323】.  It provides full‑length high‑quality audio together with rich metadata, genre hierarchies, tags and pre‑computed features【646472324112212†L319-L347】.  The dataset is distributed in several sizes: `fma_small.zip` (8 000 tracks of 30‑second excerpts, ~7.2 GiB), `fma_medium.zip` (25 000 tracks), `fma_large.zip` (106 574 tracks of 30‑second excerpts) and `fma_full.zip` (the complete tracks)【646472324112212†L349-L359】.  For prototyping you can download the small subset and extract the `.wav` files.

To build a local database:

1. Download one of the FMA subsets and extract the audio files (the dataset is provided as MP3; you can convert to WAV with `ffmpeg`).  You may also use your own music files as long as they are in uncompressed WAV format.
2. Run the database builder:
   ```bash
   python build_db.py
   ```
   This scans the `music_db` directory for `.wav` files, fingerprints each track and stores the fingerprints in `music_db/fingerprints.pkl`.  The metadata associated with each track is stored in the `metadata` dictionary.

3. Optionally, inspect the database using Python:
   ```python
   from fingerprint import FingerprintDB
   db = FingerprintDB.load('music_db/fingerprints.pkl')
   print(db.metadata)
   ```

## Desktop application

The PyQt6 application (`app.py`) provides a simple interface to recognise songs on your desktop.  It records audio in a background thread and uses Qt signals to safely update the GUI once recognition completes:

1. Ensure you have PyQt6 and the sounddevice library installed:
   ```bash
   pip install PyQt6 sounddevice
   ```
2. Build the fingerprint database as described above.
3. Run the application:
   ```bash
   python app.py
   ```
4. A window appears with a “Start Recording” button.  Play some music corresponding to a track in your database and press the button.  The app records a five‑second snippet from your microphone, computes its fingerprint and searches the database.  If a match is found, the title and (optional) artist are shown along with a score.  Otherwise “No match found” is displayed.

Because audio capture and PyQt cannot be demonstrated in this environment, the code is provided for you to run locally.  The algorithm itself can be tested in the notebook by loading a WAV file and calling `FingerprintDB.recognise(...)`.

## Customising and extending

* **Increase robustness:** Experiment with the STFT window size, hop length, amplitude threshold and fan value to achieve the best trade‑off between robustness and database size.  The default parameters work well for the synthetic example but may need tuning for real music.
* **Metadata:** The `build_db.py` script attaches simple metadata (title) derived from the filename.  When using FMA or your own collection, you can parse additional fields such as artist, album and genre and store them in the `metadata` dictionary.  The GUI displays the title and artist if available.
* **Storage back‑end:** For large databases you may wish to use a real database (e.g. SQLite) instead of an in‑memory `dict`.  The hash table can be stored in a key–value store where the key is the 32‑bit hash and the value is a list of `(track_id, offset)` tuples.
* **Real‑time recognition:** The current GUI records a fixed five‑second clip.  For real‑time recognition, stream audio in a background thread, compute hashes on the fly and stop once a confident match is detected.

## Conclusion

The provided modules illustrate the core principles behind Shazam’s industrial‑strength audio search engine: creating robust spectrogram peak constellations, combining peaks into high‑entropy hash tokens and matching by aligning time offsets【799623276281538†L130-L145】【799623276281538†L280-L338】.  By building the system from scratch you gain insight into how real music recognition services work and how to adapt them to your own applications.  To scale the system, pair the fingerprinting code with a large Creative‑Commons music dataset such as FMA【646472324112212†L319-L359】 and explore optimisations like efficient storage and parallel search.