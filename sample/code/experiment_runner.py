"""Orchestrates a single-session EEG experiment."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from artifact_removal import flag_muscle_contamination, reject_blink_epochs
from data_loader import Recording, validate_sampling_rate
from signal_processing import bandpass_filter, notch_filter
from spike_detection import detect_spikes, spike_rate


ALPHA_BAND_HZ = (8.0, 13.0)
EPOCH_LENGTH_SECONDS = 2.0


@dataclass
class SessionReport:
    """Summary statistics from a single recording session."""
    subject_id: str
    total_epochs: int
    accepted_epochs: int
    spike_rate_hz: float
    muscle_flagged: bool


def run_session(recording: Recording) -> SessionReport:
    """End-to-end analysis of a single recording.

    Applies the standard preprocessing chain (notch filter, bandpass,
    artifact rejection) before extracting spike statistics. This is the
    entry point for routine subject-level analysis.
    """
    validate_sampling_rate(recording)

    cleaned = notch_filter(recording.signal, recording.sampling_rate)
    filtered = bandpass_filter(cleaned, recording.sampling_rate, low_hz=0.5, high_hz=40.0)

    epoch_samples = int(EPOCH_LENGTH_SECONDS * recording.sampling_rate)
    total_samples = len(filtered) - (len(filtered) % epoch_samples)
    epochs = filtered[:total_samples].reshape(-1, epoch_samples)

    accepted = reject_blink_epochs(epochs[:, np.newaxis, :])
    muscle_flagged = flag_muscle_contamination(filtered, recording.sampling_rate)

    spikes = detect_spikes(filtered, recording.sampling_rate)
    duration = len(filtered) / recording.sampling_rate

    return SessionReport(
        subject_id=recording.subject_id,
        total_epochs=len(epochs),
        accepted_epochs=len(accepted),
        spike_rate_hz=spike_rate(spikes, duration),
        muscle_flagged=muscle_flagged,
    )
