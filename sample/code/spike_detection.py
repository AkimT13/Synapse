"""Threshold-based action-potential detection for extracellular recordings."""
from __future__ import annotations

import numpy as np


DEFAULT_THRESHOLD_SIGMA = 4.0
REFRACTORY_PERIOD_MS = 1.0


def detect_spikes(
    signal: np.ndarray,
    sampling_rate: float,
    threshold_sigma: float = DEFAULT_THRESHOLD_SIGMA,
) -> list[int]:
    """Return sample indices where an action potential crossed threshold.

    Threshold is defined as ``threshold_sigma`` standard deviations below the
    baseline mean (extracellular spikes are predominantly negative-going).
    A refractory period of 1 ms is enforced between successive detections so
    that a single spike is not double-counted across multiple samples.
    """
    baseline_std = np.std(signal)
    threshold = -threshold_sigma * baseline_std

    refractory_samples = int(REFRACTORY_PERIOD_MS * sampling_rate / 1000.0)
    spikes: list[int] = []
    last_spike = -refractory_samples

    for index, sample in enumerate(signal):
        if sample < threshold and index - last_spike >= refractory_samples:
            spikes.append(index)
            last_spike = index

    return spikes


def extract_waveforms(
    signal: np.ndarray,
    spike_indices: list[int],
    window_samples: int = 32,
) -> np.ndarray:
    """Cut fixed-length waveforms centered on each spike for sorting."""
    half = window_samples // 2
    waveforms = []
    for index in spike_indices:
        start = index - half
        end = index + half
        if start < 0 or end > len(signal):
            continue
        waveforms.append(signal[start:end])
    return np.array(waveforms)


def spike_rate(spike_indices: list[int], duration_seconds: float) -> float:
    """Compute the firing rate in Hz."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    return len(spike_indices) / duration_seconds
