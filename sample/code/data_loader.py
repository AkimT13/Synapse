"""Load EEG and extracellular recordings from disk."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


MINIMUM_SAMPLING_RATE_HZ = 256.0


@dataclass
class Recording:
    """A single continuous electrophysiology recording."""
    signal: np.ndarray
    sampling_rate: float
    channel_names: list[str]
    subject_id: str


def load_recording(path: str | Path) -> Recording:
    """Load a recording from a .npz file containing signal, rate, channels."""
    data = np.load(path, allow_pickle=True)
    return Recording(
        signal=data["signal"],
        sampling_rate=float(data["sampling_rate"]),
        channel_names=list(data["channel_names"]),
        subject_id=str(data["subject_id"]),
    )


def validate_sampling_rate(recording: Recording) -> None:
    """Ensure the recording meets the minimum sampling rate for spectral analysis."""
    if recording.sampling_rate < MINIMUM_SAMPLING_RATE_HZ:
        raise ValueError(
            f"Sampling rate {recording.sampling_rate} Hz is below the 256 Hz minimum "
            f"required for alias-free EEG analysis"
        )


def select_channel(recording: Recording, channel_name: str) -> np.ndarray:
    """Return a single channel's signal by name."""
    if channel_name not in recording.channel_names:
        raise KeyError(f"Channel {channel_name} not found in recording")
    index = recording.channel_names.index(channel_name)
    return recording.signal[index]
