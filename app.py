"""
app.py
======

Graphical desktop application for recognising music using
fingerprinting.  The application is built with PyQt6 and uses the
``sounddevice`` library to capture audio from the microphone.  It
invokes the fingerprinting system defined in ``fingerprint.py`` to
identify the captured snippet against a pre‑built database.

Note
----
This application requires PyQt6 and sounddevice to be installed.  If
they are not already available on your system, you can install them
with:

    pip install PyQt6 sounddevice

Because audio capture and GUI operations cannot be easily
demonstrated in this environment, the application code is provided as
a reference implementation for you to run locally.
"""

import os
import argparse
import threading
import tempfile
import uuid

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wavwrite

from fingerprint import FingerprintDB


class MainWindow(QWidget):
    """
    Main window of the MiniShazam application.

    Two Qt signals are defined to safely communicate results from the
    background recording thread back to the GUI thread:

    * ``finished`` – emitted with ``(track_id, score)`` when the
      recognition completes.
    * ``error_signal`` – emitted with a string message if an error
      occurs during recording or recognition.
    """
    # signal emitted when a recording has been processed; track_id may be None
    finished = pyqtSignal(object, int)
    # signal emitted when an exception occurs
    error_signal = pyqtSignal(str)
    def __init__(self, db_path: str):
        super().__init__()
        self.setWindowTitle("MiniShazam")
        self.db = FingerprintDB.load(db_path)

        layout = QVBoxLayout()
        self.label = QLabel("Press 'Start Recording' to identify a song")
        # Use AlignmentFlag in PyQt6
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        self.button = QPushButton("Start Recording")
        self.button.clicked.connect(self.handle_record)
        layout.addWidget(self.button)

        self.setLayout(layout)

        # Connect signals to handlers
        self.finished.connect(self.on_recognition_finished)
        self.error_signal.connect(self.on_error)

    def handle_record(self):
        # Disable button to prevent re‑entrancy
        self.button.setEnabled(False)
        self.label.setText("Recording... please make some noise!")
        duration = 5  # seconds
        sample_rate = 44100
        channels = 1

        def record_and_identify():
            try:
                # Record audio.  Blocking call runs in background thread.
                recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                                   channels=channels, dtype='float32')
                sd.wait()  # Wait until recording is finished
                # Write to a temporary WAV file
                tmpdir = tempfile.gettempdir()
                tmpfile = os.path.join(tmpdir, f"recording_{uuid.uuid4().hex}.wav")
                # Convert float32 [-1,1] to 16‑bit PCM
                audio_int16 = np.int16(recording[:, 0] * 32767)
                wavwrite(tmpfile, sample_rate, audio_int16)
                # Recognise the recording
                track_id, score = self.db.recognise(tmpfile)
                # Remove temp file
                try:
                    os.remove(tmpfile)
                except OSError:
                    pass
                # Emit result via signal.  Use emit() to notify the GUI thread.
                self.finished.emit(track_id, score)
            except Exception as e:
                # Emit error via signal
                self.error_signal.emit(str(e))

        # Start background thread
        threading.Thread(target=record_and_identify, daemon=True).start()

    def on_recognition_finished(self, track_id: object, score: int) -> None:
        """
        Slot called in the GUI thread when a recording has been
        processed.  Updates the label with the result and re‑enables
        the record button.
        """
        # Score threshold: require at least 5 matching hash tokens
        if track_id is None or score < 5:
            self.label.setText("No match found")
        else:
            meta = self.db.metadata.get(track_id, {})
            title = meta.get("title", "Unknown title")
            artist = meta.get("artist", "Unknown artist")
            self.label.setText(f"Matched: {title} by {artist}\nScore: {score}")
        self.button.setEnabled(True)

    def on_error(self, message: str) -> None:
        """
        Slot called in the GUI thread when an exception occurs.  Displays
        an error message box and resets the UI state.
        """
        QMessageBox.critical(self, "Error", message)
        self.button.setEnabled(True)
        self.label.setText("Press 'Start Recording' to identify a song")


def main():
    parser = argparse.ArgumentParser(description="MiniShazam desktop app")
    parser.add_argument(
        "--db-path",
        default=os.path.join(os.getcwd(), "music_db", "fingerprints.pkl"),
        help="Path to fingerprint database (.pkl).",
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db_path)
    if not os.path.isfile(db_path):
        raise FileNotFoundError(
            f"Fingerprint database not found at {db_path}. Please run build_db.py first."
        )
    app = QApplication([])
    window = MainWindow(db_path)
    window.resize(400, 200)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
